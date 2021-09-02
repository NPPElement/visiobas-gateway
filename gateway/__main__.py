import asyncio
import logging
import sys

from gateway.gateway_ import Gateway
from gateway.models.settings import GatewaySettings, LogSettings
from gateway.utils import ExtraFormatter


def setup_logging(settings: LogSettings) -> None:
    for name in settings.disable_loggers:
        _logger = logging.getLogger(name=name)
        _logger.propagate = False

    root_log = logging.getLogger()
    root_log.setLevel(settings.level)
    hdlr = logging.StreamHandler(stream=sys.stderr)
    fmt = ExtraFormatter(fmt=settings.format)
    hdlr.setFormatter(fmt=fmt)
    root_log.addHandler(hdlr=hdlr)


async def load_and_run() -> None:
    gateway = await Gateway.create(settings=GatewaySettings())
    await gateway.async_run()


def main() -> None:
    log_settings = LogSettings()
    setup_logging(settings=log_settings)

    asyncio.run(load_and_run())


if __name__ == "__main__":
    main()
