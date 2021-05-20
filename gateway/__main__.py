import asyncio
import logging
import os
import sys

# from aiomisc.log import basic_config
from gateway.gateway_ import VisioBASGateway
from gateway.models import GatewaySettings
from gateway.utils import ExtraFormatter

# Set logging
LOG_LEVEL = os.getenv('GW_LOG_LEVEL', 'DEBUG')
LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(levelname)-8s [%(asctime)s] %(name)s'
                                          '.%(funcName)s(%(lineno)d): %(message)s')

loggers_to_disable = ['pymodbus', ]  # 'BAC0_Root', 'bacpypes',]
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
    # unused_loggers = ('BAC0_Root.BAC0.scripts.Base.Base',
    #                   'BAC0_Root.BAC0.scripts.Lite.Lite',
    #                   'BAC0_Root.BAC0.tasks.UpdateCOV.Update_local_COV',
    #                   'BAC0_Root.BAC0.tasks.TaskManager.Manager',
    #                   'BAC0_Root.BAC0.tasks.RecurringTask.RecurringTask',
    #                   'bacpypes.iocb._statelog',
    #                   'bacpypes.task',
    #
    #                   # 'pymodbus.client.sync',
    #                   # 'pymodbus.client.asynchronous.async_io',
    #                   # 'pymodbus.transaction',
    #                   # 'pymodbus.framer.socket_framer',
    #                   # 'pymodbus.framer.rtu_framer',
    #                   # 'pymodbus.factory',
    #                   # 'pymodbus.payload',
    #                   )
    # disable_loggers(loggers=unused_loggers)
    asyncio.run(load_and_run())


if __name__ == '__main__':
    main()
