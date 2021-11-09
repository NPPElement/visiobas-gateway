import asyncio
import logging
import sys

from visiobas_gateway.gateway import Gateway
from visiobas_gateway.schemas.settings import (
    ApiSettings,
    GatewaySettings,
    HTTPSettings,
    LogSettings,
    MQTTSettings,
)
from visiobas_gateway.utils import ExtraFormatter

try:
    import uvloop  # type: ignore

    _UVLOOP_ENABLE = True
except ImportError:
    _UVLOOP_ENABLE = False


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
    gateway = await Gateway.create(
        gateway_settings=GatewaySettings(),
        api_settings=ApiSettings(),
        clients_settings=[MQTTSettings(), HTTPSettings()],
    )
    await gateway.run()


def main() -> None:
    setup_logging(settings=LogSettings())

    if _UVLOOP_ENABLE:
        uvloop.install()
    asyncio.run(load_and_run())


if __name__ == "__main__":
    main()
