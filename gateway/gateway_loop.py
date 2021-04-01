import asyncio
from pathlib import Path
from typing import Callable, Any

from gateway.clients import VisioBASHTTPClient, VisioBASMQTTClient


class VisioBASGateway:
    """VisioBAS IoT Gateway."""

    _base_dir = Path(__file__).resolve().parent
    _cfg_dir = _base_dir / 'config'

    def __init__(self, config: dict):
        self.loop = asyncio.get_running_loop()
        # self._pending_tasks: list = []
        self.config = config

        self._stopped: asyncio.Event | None = None
        self._upd_task: asyncio.Task | None = None

        self.http_client: VisioBASHTTPClient = None
        self.mqtt_client: VisioBASMQTTClient = None
        self.http_api_server = None
        self.verifier = None  # verifier(non-threaded)

    @classmethod
    def from_yaml(cls, yaml_path: Path):
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

    async def async_start(self):
        await self.add_job(self.async_setup)
        # self.loop.run_forever()

    async def async_setup(self):
        """Set up Gateway and spawn update task.

        Setup gateway steps:
            - Log in to HTTP
            - Get device id list
            - Get device data via HTTP
            - Start devices poll
            - Connect to MQTT
        """
        self.http_client = VisioBASHTTPClient.from_yaml(
            gateway=self, yaml_path=self._cfg_dir / 'http.yaml'
        )
        await self.http_client.setup()

        self.mqtt_client = VisioBASMQTTClient.from_yaml(
            gateway=self, yaml_path=self._cfg_dir / 'mqtt.yaml'
        )
        # todo: setup http api server

        self._upd_task = self.loop.create_task(self.periodic_update())

    async def periodic_update(self) -> None:
        """Spawn periodic update task.

        Update gateway steps:
            - Unsubscribe to MQTT
            - Stop devices poll
            - Log out to HTTP # fixme
            - Log in to HTTP
            - Update device ids
            - Request device data via HTTP
            - Start devices poll
            - Subscribe to MQTT topics
        """
        await asyncio.sleep(delay=self.upd_period)

        await self.mqtt_client.unsubscribe(self.mqtt_client.topics)
        # await stop_devices()
        await self.http_client.logout(nodes=self.http_client.all_nodes)
        # await update device id list
        await self.http_client.authorize()
        # await self.http_client.rq_devices_data()
        # await parse_device_data()
        # await self.start_devices_poll
        await self.mqtt_client.subscribe(self.mqtt_client.topics)

        self._upd_task = self.loop.create_task(self.periodic_update())

    def add_job(self, target: Callable, *args: Any) -> asyncio.Future | None:
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
        if self._stopped is not None:
            self._stopped.set()

    async def _perform_stop_tasks(self) -> None:
        pass
        # todo implement then use in upd
