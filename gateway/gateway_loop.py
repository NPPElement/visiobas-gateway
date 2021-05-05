import asyncio
from pathlib import Path
from typing import Callable, Any, Optional, Iterable, Union, Awaitable

import aiojobs
from pydantic import ValidationError

from gateway.clients import VisioBASHTTPClient, VisioBASMQTTClient
from gateway.devices.async_modbus import AsyncModbusDevice
from gateway.models import ObjType, BACnetDeviceModel, ModbusObjModel, Protocol
from gateway.utils import read_address_cache, get_file_logger
from gateway.verifier import BACnetVerifier
# _log = getLogger(__name__)


_LOG = get_file_logger(__name__)


class VisioBASGateway:
    """VisioBAS IoT Gateway."""

    BASE_DIR = Path(__file__).resolve().parent
    CFG_DIR = BASE_DIR / 'config'

    HTTP_CFG_PATH = CFG_DIR / 'http.yaml'
    MQTT_CFG_PATH = CFG_DIR / 'mqtt.yaml'

    BACNET_ADDRESS_CACHE_PATH = BASE_DIR / 'connectors/bacnet/address_cache'
    MODBUS_ADDRESS_CACHE_PATH = BASE_DIR / 'devices/modbus_address_cache'
    MODBUS_RTU_ADDRESS_CACHE_PATH = 'connectors/modbus/rtu.yaml'

    def __init__(self, config: dict):
        # self.loop = asyncio.new_event_loop()
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        self.pymodbus_loop: asyncio.AbstractEventLoop = None
        # self._pending_tasks: list = []
        self.config = config

        self._stopped: asyncio.Event = None
        self._upd_task: asyncio.Task = None

        self._scheduler: aiojobs.Scheduler = None

        self.http_client: VisioBASHTTPClient = None
        self.mqtt_client: VisioBASMQTTClient = None
        self.http_api_server = None
        self.verifier = BACnetVerifier(config=config.get('verifier'))

        self._devices: dict[int, Union[AsyncModbusDevice]] = {}

    @classmethod
    async def create(cls, config: dict) -> 'VisioBASGateway':
        gateway = cls(config=config)
        gateway._scheduler = await aiojobs.create_scheduler(close_timeout=60,
                                                            limit=100)
        return gateway

    @classmethod
    async def from_yaml(cls, yaml_path: Path) -> 'VisioBASGateway':
        # todo add a pydantic model of config and use it
        """Create gateway with configuration, read from YAML file."""
        import yaml

        with yaml_path.open() as cfg_file:
            cfg = yaml.load(cfg_file, Loader=yaml.FullLoader)
        gateway = await cls.create(config=cfg)
        return gateway

    @property
    def upd_period(self) -> int:
        return self.config.get('upd_period', 3600)

    @property
    def devices(self) -> dict[int, Union[AsyncModbusDevice]]:
        return self._devices

    # def run(self) -> None:
    #     # if need, set event loop policy here
    #     asyncio.run(self.async_run(), debug=True)

    async def async_run(self) -> None:
        """Gateway main entry point.
        Start Gateway and block until stopped.
        """
        # self.async_stop will set this instead of stopping the loop
        self._stopped = asyncio.Event()
        await self.async_start()

        await self._stopped.wait()

    async def async_start(self) -> None:
        await self.async_add_job(self.async_setup)

        # self.loop.run_forever()

    async def async_setup(self) -> None:
        """Set up Gateway and spawn update task."""
        self.http_client = VisioBASHTTPClient.from_yaml(
            gateway=self, yaml_path=self.HTTP_CFG_PATH)
        # await self.http_client.setup()
        # self.mqtt_client = VisioBASMQTTClient.from_yaml(
        #     gateway=self, yaml_path=self.MQTT_CFG_PATH)
        # todo: setup HTTP API server
        await self._scheduler.spawn(coro=self.periodic_update())
        # self._upd_task = self.loop.create_task(self.periodic_update())

    async def periodic_update(self) -> None:
        """Spawn periodic update task."""
        await self._perform_start_tasks()
        await asyncio.sleep(delay=self.upd_period)
        await self._perform_stop_tasks()

        await self._scheduler.spawn(self.periodic_update())
        # self._upd_task = self.loop.create_task(self.periodic_update())

    def add_job(self, target: Callable, *args: Any) -> None:
        """Adds job to the executor pool.

        Args:
            target: target to call.
            args: parameters for target to call.
        """
        if target is None:
            raise ValueError('None not allowed')
        self.loop.call_soon_threadsafe(self.async_add_job, target, *args)

    def async_add_job(self, target: Callable, *args: Any
                      ) -> Optional[Union[asyncio.Future, Awaitable]]:
        """Adds a job from within the event loop.

        Args:
            target: target to call.
            args: parameters for target to call.
        """
        if target is None:
            raise ValueError('None not allowed')

        if asyncio.iscoroutine(target) or asyncio.iscoroutinefunction(target):
            # await self._scheduler.spawn(target(*args))
            task = self.loop.create_task(target(*args))
            return task
        else:
            task = self.loop.run_in_executor(None, target, *args)
            return task

    async def async_stop(self) -> None:
        """Stops Gateway."""
        # todo wait pending tasks
        if self._stopped is not None:
            self._stopped.set()

    async def _perform_start_tasks(self) -> None:
        """Performs starting tasks.

        Setup gateway steps:
            - Log in to HTTP
            - Load devices
            - Start devices poll
            - Connect to MQTT
        """
        await self.http_client.authorize()

        # Update devices identifiers to poll
        device_ids = await self.async_add_job(target=self._get_device_ids)

        # Load devices
        load_device_tasks = [self.load_device(dev_id=dev_id) for dev_id in device_ids]
        await asyncio.gather(*load_device_tasks)

        start_poll_tasks = [self.start_device_poll(dev_id=dev_id)
                            for dev_id in self._devices.keys()]
        await asyncio.gather(*start_poll_tasks)
        # todo await self.mqtt_client.subscribe(self.mqtt_client.topics)

    async def _perform_stop_tasks(self) -> None:
        """Performs stopping tasks.

        Stop gateway steps:
            - Unsubscribe to MQTT
            - Stop devices poll
            - Log out to HTTP
        """
        # todo await self.mqtt_client.unsubscribe(self.mqtt_client.topics)
        # todo await stop_devices()
        await self.http_client.logout(nodes=self.http_client.all_nodes)

    async def load_device(self, dev_id: int) -> None:
        """Tries to download an object of device from server.
        Then gets objects to poll and load them into device.

        When device loaded, it may be accessed by `gateway.devices[identifier]`.

        If fails get objects from server - loads it from local.
        """
        try:
            dev_obj_data = await self.http_client.get_objs(dev_id=dev_id,
                                                           obj_types=(ObjType.DEVICE,))
            _LOG.debug('Device object downloaded',  #: {dev_obj_data}',
                       extra={'device_id': dev_id})

            if not dev_obj_data:
                _LOG.warning('Empty device object', extra={'device_id': dev_id})
                return None

            # objs in the list, so get [0] element in `dev_obj_data[0]` below
            dev_obj = await self.async_add_job(self._parse_device_obj, dev_obj_data[0])

            device = await self.device_factory(dev_obj=dev_obj)

            # fixme use for task in asyncio.as_completed(tasks):
            objs_data = await self.http_client.get_objs(dev_id=dev_id,
                                                        obj_types=device.types_to_rq)
            _LOG.debug('Objects to poll downloaded', extra={'device_id': dev_id})

            extract_tasks = [self.async_add_job(self._extract_objects, obj_data, dev_obj)
                             for obj_data in objs_data]
            objs_lists = await asyncio.gather(*extract_tasks)
            objs = [obj for lst in objs_lists for obj in lst]  # flat list of lists

            if len(objs):  # if there are objects
                _LOG.warning(f'Objects to poll: {len(objs)}', extra={'device_id': dev_id})
                await self.async_add_job(device.load_objects, objs)
            else:
                _LOG.warning("There aren't objects to poll", extra={'device_id': dev_id})

            self._devices.update({device.id: device})
            _LOG.info(f'Device loaded', extra={'device_id': dev_id})
        except AttributeError as e:
            _LOG.exception(f'Cannot load device: {e}', extra={'device_id': dev_id})

    async def start_device_poll(self, dev_id: int) -> None:
        """Starts poll of device."""
        await self.async_add_job(self.devices[dev_id].start_periodic_polls)
        _LOG.info('Device polling started', extra={'device_id': dev_id})

    @staticmethod
    def _parse_device_obj(dev_data: dict) -> BACnetDeviceModel:
        """Parses and validate device object data from JSON.

        Returns:
            parsed and validated device object.
        """
        try:
            dev_obj = BACnetDeviceModel(**dev_data)
            _LOG.debug(f'Device object parsed', extra={'device_object': str(dev_obj)})
            return dev_obj
        except ValidationError as e:
            _LOG.exception(f'Cannot parse device object {e}')

    def _extract_objects(self, objs_data: tuple, dev_obj: BACnetDeviceModel
                         ) -> list[ModbusObjModel]:
        """Parses and validate objects data from JSON.

        Returns:
            List of parsed and validated objects.
        """
        objs = [self.object_factory(dev_obj=dev_obj, obj_data=obj_data)
                for obj_data in objs_data
                if not None]
        # _log.debug('Objects to poll created', extra={'device_id': dev_obj.id})
        return objs

    def _get_device_ids(self) -> Iterable[int]:
        """Gets devise identifiers to poll.

        Returns:
            Device identifiers to poll.
        """
        # todo get from gateway object
        return read_address_cache(path=self.MODBUS_ADDRESS_CACHE_PATH).keys()

    async def device_factory(self, dev_obj: BACnetDeviceModel) -> Union[AsyncModbusDevice]:
        """Creates device for provided protocol.

        Returns:
            Created device.
        # Raises:
        #     ValueError: if unexpected protocol provided.
        #     # todo add parse model error
        """
        try:
            protocol = dev_obj.property_list.protocol
            if protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTU}:
                device = await AsyncModbusDevice.create(device_obj=dev_obj, gateway=self)

                # await device.create_client()
                # self.add_job(device.connect_client)
            elif protocol == Protocol.BACNET:
                device = None  # todo
            else:
                _LOG.warning('Unexpected protocol', extra={'protocol': protocol,
                                                           'device_id': dev_obj.id})
                raise ValueError('Unexpected protocol')

            _LOG.debug('Device object created', extra={'device_id': device.id})
            return device
        except Exception as e:
            _LOG.exception(f'Failed device creation {e}', extra={'device_id': dev_obj.id})

    @staticmethod
    def object_factory(dev_obj: BACnetDeviceModel, obj_data: dict[str, Any]
                       ) -> Optional[Union[ModbusObjModel]]:
        """Creates object for provided protocol data.

        Returns:
            If object created - returns created object.
            If object incorrect - returns None.
        """
        try:
            protocol = dev_obj.property_list.protocol
            if protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTU}:
                obj = ModbusObjModel(**obj_data)  # todo switch to parse_raw
            elif protocol == Protocol.BACNET:
                obj = None  # todo
            else:
                # unknown protocols logging by `pydantic` on enter
                raise ValueError('Unexpected protocol')
            return obj
        except ValidationError as e:
            _LOG.exception(f'Failed parsing: {dev_obj.id}: {obj_data}: {e}')
