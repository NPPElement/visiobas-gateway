import asyncio
from logging import getLogger
from pathlib import Path
from typing import Callable, Any, Optional, Awaitable, Iterable, Union

from gateway.clients import VisioBASHTTPClient, VisioBASMQTTClient
from gateway.devices.async_device import AsyncModbusDevice
from gateway.models import ObjType, BACnetDeviceModel, ModbusObjModel
from gateway.utils import read_address_cache

_log = getLogger(__name__)


class VisioBASGateway:
    """VisioBAS IoT Gateway."""

    BASE_DIR = Path(__file__).resolve().parent
    CFG_DIR = BASE_DIR / 'config'

    BACNET_ADDRESS_CACHE_PATH = BASE_DIR / 'connectors/bacnet/address_cache'
    MODBUS_ADDRESS_CACHE_PATH = BASE_DIR / 'connectors/modbus/address_cache'
    MODBUS_RTU_ADDRESS_CACHE_PATH = 'connectors/modbus/rtu.yaml'

    def __init__(self, config: dict):
        self.loop = asyncio.get_running_loop()
        # self._pending_tasks: list = []
        self.config = config

        self._stopped: asyncio.Event = None
        self._upd_task: asyncio.Task = None

        self.http_client: VisioBASHTTPClient = None
        self.mqtt_client: VisioBASMQTTClient = None
        self.http_api_server = None
        self.verifier = None  # verifier(non-threaded)

        self._devices = dict[int, Any]

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
    def devices(self) -> dict[int, Any]:
        return self._devices

    def run(self) -> None:
        # if need, set event loop policy here
        asyncio.run(self.async_run())

    async def async_run(self) -> None:
        """Gateway main entry point.
        Start Gateway and block until stopped.
        """
        # self.async_stop will set this instead of stopping the loop
        self._stopped = asyncio.Event()
        await self.async_start()

        await self._stopped.wait()

    async def async_start(self) -> None:
        await self.add_job(self.async_setup)
        # self.loop.run_forever()

    async def async_setup(self) -> None:
        """Set up Gateway and spawn update task."""
        self.http_client = VisioBASHTTPClient.from_yaml(
            gateway=self, yaml_path=self.CFG_DIR / 'http.yaml')
        # await self.http_client.setup()
        self.mqtt_client = VisioBASMQTTClient.from_yaml(
            gateway=self, yaml_path=self.CFG_DIR / 'mqtt.yaml')
        # todo: setup HTTP API server
        self._upd_task = self.loop.create_task(self.periodic_update())

    async def periodic_update(self) -> None:
        """Spawn periodic update task."""
        await self._perform_start_tasks()
        await asyncio.sleep(delay=self.upd_period)
        await self._perform_stop_tasks()

        self._upd_task = self.loop.create_task(self.periodic_update())

    def add_job(self, target: Callable, *args: Any) -> Optional[Awaitable]:
        """Add a job."""
        if target is None:
            raise ValueError('None not allowed')

        if asyncio.iscoroutine(target):
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
        device_ids = await self.add_job(target=self._get_device_ids)

        # Load devices
        load_device_tasks = [self.load_device(dev_id=dev_id) for dev_id in device_ids]
        await asyncio.gather(*load_device_tasks)

        # todo await self.start_devices_poll
        await self.mqtt_client.subscribe(self.mqtt_client.topics)

    async def _perform_stop_tasks(self) -> None:
        """Performs stopping tasks.

        Stop gateway steps:
            - Unsubscribe to MQTT
            - Stop devices poll
            - Log out to HTTP
        """
        await self.mqtt_client.unsubscribe(self.mqtt_client.topics)
        # await stop_devices() todo
        await self.http_client.logout(nodes=self.http_client.all_nodes)

    async def load_device(self, dev_id: int) -> None:
        """Tries to download an object of device from server.
        Then gets objects to poll and load them into device.

        When device loaded, it may be accessed by `gateway.devices[identifier]`.

        If fails get objects from server - loads it from local.
        """
        dev_obj = await self.http_client.get_objs(dev_id=dev_id,
                                                  obj_types=(ObjType.DEVICE,))
        device = await self.add_job(self.device_factory, dev_obj)

        objs_data = await self.http_client.get_objs(dev_id=dev_id,
                                                    obj_types=device.types_to_rq)
        objs = await self.add_job(self._extract_objects, objs_data, dev_obj)
        if len(objs):
            device.load_objects(objs=objs)
        self._devices.update({device.id: device})

    async def start_device_poll(self, dev_id: int) -> None:
        """Starts poll of device."""

    def _extract_objects(self, objs_data: tuple, dev_obj: BACnetDeviceModel
                         ) -> list[ModbusObjModel]:
        """Parses and validate objects data from JSON.

        Returns:
            List of parsed and validated objects.
        """
        objs = [self.object_factory(dev_obj=dev_obj, obj_data=obj_data)
                for obj_data in objs_data
                if not None]
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
        protocol = dev_obj.protocol
        if protocol == 'ModbusTCP' or protocol == 'ModbusRTU':
            device = AsyncModbusDevice(device_obj=dev_obj, gateway=self)
        elif protocol == 'BACnet':
            device = None  # todo
        else:
            raise ValueError(f'Unexpected protocol: {protocol}({dev_obj.id})')
        return device

    @staticmethod
    def object_factory(dev_obj: BACnetDeviceModel, obj_data: dict[str, Any]
                       ) -> Optional[Union[ModbusObjModel]]:
        """Creates object for provided protocol.

        Returns:
            If object created - returns created object.
            If object incorrect - returns None.
        """
        try:
            protocol = dev_obj.protocol
            if protocol == 'ModbusTCP' or protocol == 'ModbusRTU':
                obj = ModbusObjModel.parse_raw(**obj_data)
            elif protocol == 'BACnet':
                obj = None  # todo
            else:
                raise ValueError(f'Unexpected protocol: {protocol}({dev_obj.id})')
            return obj
        except Exception as e:  # fixme catch parsing error
            _log.warning(f'Failed parsing: {dev_obj.id}: {obj_data}: {e}')
