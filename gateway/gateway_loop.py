import asyncio
from logging import getLogger
from pathlib import Path
from typing import Callable, Any, Optional, Iterable, Union

from gateway.clients import VisioBASHTTPClient, VisioBASMQTTClient
from gateway.devices.async_device import AsyncModbusDevice
from gateway.models import ObjType, BACnetDeviceModel, ModbusObjModel, Protocol
from gateway.utils import read_address_cache

_log = getLogger(__name__)


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
        self.loop = asyncio.get_running_loop()
        # self._pending_tasks: list = []
        self.config = config

        self._stopped: asyncio.Event = None
        self._upd_task: asyncio.Task = None

        self.http_client: VisioBASHTTPClient = None
        self.mqtt_client: VisioBASMQTTClient = None
        self.http_api_server = None
        self.verifier = None  # verifier(non-threaded)

        self._devices: dict[int, Union[AsyncModbusDevice]] = {}

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'VisioBASGateway':
        # todo add a pydantic model of config and use it
        """Create gateway with configuration, read from YAML file."""
        import yaml

        with yaml_path.open() as cfg_file:
            cfg = yaml.load(cfg_file, Loader=yaml.FullLoader)
        return cls(config=cfg)

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
        self._upd_task = self.loop.create_task(self.periodic_update())

    async def periodic_update(self) -> None:
        """Spawn periodic update task."""
        await self._perform_start_tasks()
        await asyncio.sleep(delay=self.upd_period)
        await self._perform_stop_tasks()

        self._upd_task = self.loop.create_task(self.periodic_update())

    # def add_job(self, target: Callable, *args: Any) -> None:
    #     """Adds job to the executor pool.
    #
    #     Args:
    #         target: target to call.
    #         args: parameters for target to call.
    #     """
    #     if target is None:
    #         raise ValueError('None not allowed')
    #     self.loop.call_soon_threadsafe(self.async_add_job, target, *args)

    def async_add_job(self, target: Callable, *args: Any) -> Optional[asyncio.Future]:
        """Adds a job from within the event loop.

        Args:
            target: target to call.
            args: parameters for target to call.
        """
        if target is None:
            raise ValueError('None not allowed')

        if asyncio.iscoroutine(target) or asyncio.iscoroutinefunction(target):
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
                            for dev_id in device_ids]
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
            _log.debug('Device object downloaded',  #: {dev_obj_data}',
                       extra={'device_id': dev_id})
            # objs in the list, so get [0] element in `dev_obj_data[0]` below
            dev_obj = await self.async_add_job(self._parse_device_obj, dev_obj_data[0])
            device = await self.async_add_job(self.device_factory, dev_obj)

            objs_data = await self.http_client.get_objs(dev_id=dev_id,
                                                        obj_types=device.types_to_rq)
            _log.debug('Objects to poll downloaded', extra={'device_id': dev_id})
            # objs in the list, so get [0] element in `objs_data[0]` below
            objs = await self.async_add_job(self._extract_objects, objs_data[0], dev_obj)

            if len(objs):  # if there are objects
                await self.async_add_job(device.load_objects, objs)

            self._devices.update({device.id: device})
            _log.info(f'Device loaded', extra={'device_id': dev_id})
        except AttributeError as e:
            _log.exception(f'Cannot load device: {e}', extra={'device_id': dev_id})

    async def start_device_poll(self, dev_id: int) -> None:
        """Starts poll of device."""
        await self.async_add_job(self.devices[dev_id].start_periodic_polls)
        _log.debug('Poll od device started', extra={'device_id': dev_id})

    @staticmethod
    def _parse_device_obj(dev_data: dict) -> BACnetDeviceModel:
        """Parses and validate device object data from JSON.

        Returns:
            parsed and validated device object.
        """
        dev_obj = BACnetDeviceModel(**dev_data)
        _log.debug(f'Device object parsed', extra={'device_object': str(dev_obj)})
        return dev_obj

    def _extract_objects(self, objs_data: tuple, dev_obj: BACnetDeviceModel
                         ) -> list[ModbusObjModel]:
        """Parses and validate objects data from JSON.

        Returns:
            List of parsed and validated objects.
        """
        objs = [self.object_factory(dev_obj=dev_obj, obj_data=obj_data)
                for obj_data in objs_data
                if not None]
        _log.debug('Objects to poll created', extra={'device_id': dev_obj.id})
        return objs

    def _get_device_ids(self) -> Iterable[int]:
        """Gets devise identifiers to poll.

        Returns:
            Device identifiers to poll.
        """
        # todo get from gateway object
        return read_address_cache(path=self.MODBUS_ADDRESS_CACHE_PATH).keys()

    def device_factory(self, dev_obj: BACnetDeviceModel) -> Union[AsyncModbusDevice]:
        """Creates device for provided protocol.

        Returns:
            Created device.
        Raises:
            ValueError: if unexpected protocol provided.
            # todo add parse model error
        """
        protocol = dev_obj.property_list.protocol
        if protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTU}:
            device = AsyncModbusDevice(device_obj=dev_obj, gateway=self)
        elif protocol == Protocol.BACNET:
            device = None  # todo
        else:
            _log.warning('Unexpected protocol', extra={'protocol': protocol,
                                                       'device_id': dev_obj.id})
            raise ValueError('Unexpected protocol')
        _log.debug('Device object created', extra={'device_id': device.id})
        return device

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
                # unknown protocols logging by pydantic on enter
                raise ValueError('Unexpected protocol')
            return obj
        except AttributeError as e:
            _log.exception(f'Failed parsing: {dev_obj.id}: {obj_data}: {e}')
