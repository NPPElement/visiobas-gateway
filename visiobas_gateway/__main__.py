import asyncio
import logging
import sys

import uvloop  # type: ignore

from visiobas_gateway.gateway_ import Gateway
from visiobas_gateway.models.settings import GatewaySettings, LogSettings
from visiobas_gateway.utils import ExtraFormatter


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

    uvloop.install()
    asyncio.run(load_and_run())


if __name__ == "__main__":
    main()
