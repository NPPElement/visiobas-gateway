import asyncio
from pathlib import Path
from typing import Callable, Any


class VisioBASGateway:
    def __init__(self, config: dict):
        self.loop = asyncio.get_running_loop()
        # self._pending_tasks: list = []
        self.config = config

        self._stopped: asyncio.Event | None = None

        self.http_client = None
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
        # _async_stop will set this instead of stopping the loop
        self._stopped = asyncio.Event()
        await self.async_start()

        await self._stopped.wait()

    async def async_start(self):
        """Gateway main entry point.
        Start Gateway and block until stopped.
        """
        await self.add_job(self.async_setup)
        # self.loop.run_forever()

    async def async_setup(self):
        pass
        # todo use add_job for all
        # setup http client
        # setup mqtt
        # setup http api server

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



