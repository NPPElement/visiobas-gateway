import asyncio
from pathlib import Path
from typing import Callable, Any

from gateway.clients import VisioBASHTTPClient


class VisioBASGateway:
    """VisioBAS IoT Gateway."""

    _base_dir = Path(__file__).resolve().parent
    _cfg_dir = _base_dir / 'config'

    def __init__(self, config: dict):
        self.loop = asyncio.get_running_loop()
        # self._pending_tasks: list = []
        self.config = config

        self._stopped: asyncio.Event | None = None

        self.http_client: VisioBASHTTPClient | None = None
        self.mqtt_client = None
        self.http_api_server = None
        self.verifier = None  # verifier(non-threaded)

    @classmethod
    def from_yaml(cls, yaml_path: Path):
        """Create gateway with configuration, read from YAML file."""
        import yaml

        with yaml_path.open() as cfg_file:
            cfg = yaml.load(cfg_file, Loader=yaml.FullLoader)
        return cls(config=cfg)

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
        """Set up Gateway.

        Note: Used gateway.add_job in all to start serve."""
        self.http_client = VisioBASHTTPClient.from_yaml(
            gateway=self,
            yaml_path=self._cfg_dir / 'http.yaml'
        )
        await self.http_client.setup()
        # setup mqtt
        # setup http api server

    async def periodic_update(self):
        """Spawn periodic update task.

        Update contains:
            - Update device ids
            - Reauthorize by HTTP
            - resubscribe to MQTT topics
        """
        # todo

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
