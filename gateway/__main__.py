import asyncio
import logging
import os
import sys

# from aiomisc.log import basic_config
from gateway.gateway_ import VisioBASGateway
from gateway.models import GatewaySettings
from gateway.utils import ExtraFormatter

# Set logging
LOG_LEVEL = os.getenv('GTW_LOG_LEVEL', 'DEBUG')
LOG_FORMAT = os.environ.get('LOG_FORMAT',
                            '%(levelname)-8s [%(asctime)s] %(name)s'
                            '.%(funcName)s(%(lineno)d): %(message)s')
# [%(threadName)s]

loggers_to_disable = ['pymodbus', 'asyncio', ]  # 'BAC0_Root', 'bacpypes',]
for name in loggers_to_disable:
    _logger = logging.getLogger(name=name)
    _logger.propagate = False

root_log = logging.getLogger()
root_log.setLevel(LOG_LEVEL)
hdlr = logging.StreamHandler(stream=sys.stderr)
fmt = ExtraFormatter(fmt=LOG_FORMAT)
hdlr.setFormatter(fmt=fmt)
root_log.addHandler(hdlr=hdlr)


# logging.basicConfig(format=LOG_FORMAT,
#                     level=LOG_LEVEL,
#                     stream=sys.stdout)

# basic_config(level=logging.DEBUG, buffered=True, flush_interval=2,
#              # log_format=_log_fmt,
#              stream=sys.stderr
#              )

async def load_and_run() -> None:
    gateway = await VisioBASGateway.create(settings=GatewaySettings())
    await gateway.async_run()


def main():
    asyncio.run(load_and_run())


if __name__ == '__main__':
    main()
