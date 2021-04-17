import asyncio
from pathlib import Path
from typing import Callable, Any, Optional, Awaitable, Iterable

from gateway.clients import VisioBASHTTPClient, VisioBASMQTTClient
from gateway.connectors.modbus.async_device import AsyncModbusDevice
from gateway.models import ObjType, BACnetDeviceModel
from gateway.utils import read_address_cache


class VisioBASGateway:
    """VisioBAS IoT Gateway."""

    _base_dir = Path(__file__).resolve().parent
    _cfg_dir = _base_dir / 'config'

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

        # self.bacnet = list[BACnetDevice]
        # self.modbus = list[ModbusDevice]

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
            gateway=self, yaml_path=self._cfg_dir / 'http.yaml')
        # await self.http_client.setup()

        self.mqtt_client = VisioBASMQTTClient.from_yaml(
            gateway=self, yaml_path=self._cfg_dir / 'mqtt.yaml')
        # todo: setup http api server
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
        """Stop Gateway."""
        # todo wait pending tasks
        if self._stopped is not None:
            self._stopped.set()

    async def _perform_start_tasks(self) -> None:
        """Perform starting tasks.

        Setup gateway steps:
            - Log in to HTTP
            - Get device id list (HTTP?)
            - Get device data via HTTP
            - Start devices poll
            - Connect to MQTT
        """
        # todo

        await self.http_client.authorize()

        # await update device id list
        device_ids = await self.add_job(target=self._get_device_ids)

        # await self.http_client.rq_devices_data()
        # await self.http_client.rq_objects_data()
        # await self.start_devices_poll
        await self.mqtt_client.subscribe(self.mqtt_client.topics)

    async def _perform_stop_tasks(self) -> None:
        """Perform stopping tasks.

        Stop gateway steps:
            - Unsubscribe to MQTT
            - Stop devices poll
            - Log out to HTTP
        """
        await self.mqtt_client.unsubscribe(self.mqtt_client.topics)
        # await stop_devices() todo
        await self.http_client.logout(nodes=self.http_client.all_nodes)

    def _get_device_ids(self) -> Iterable[int]:
        # todo get from gateway object
        return read_address_cache(
            path=self._base_dir / 'connectors/modbus/address_cache').keys()

    async def _get_devices_objs(self, device_ids: Iterable[int]) -> list[
        BACnetDeviceModel]:  # fixme type
        rq_dev_tasks = [self.http_client.get_objs(device_id=dev_id,
                                                  obj_types=(ObjType.DEVICE,))
                        for dev_id in device_ids]
        devices_data = await asyncio.gather(*rq_dev_tasks)

        devices = [BACnetDeviceModel.parse_raw(**dev_data) for dev_data in devices_data]
        return devices

    def setup_device(self, dev_obj: BACnetDeviceModel) -> None:
        device = self.device_factory(dev_obj=dev_obj)
        self._devices.update({device.id: device})

    def device_factory(self, dev_obj: BACnetDeviceModel) -> Optional[Any]:
        protocol = dev_obj.protocol
        if protocol == 'ModbusTCP' or protocol == 'ModbusRTU':
            device = AsyncModbusDevice(device_obj=dev_obj, gateway=self)
        elif protocol == 'BACnet':
            device = None  # todo
        else:
            raise ValueError(f'Unexpected protocol passed: {protocol}({dev_obj.id})')
        return device
