import asyncio
import logging
import os
import sys
from pathlib import Path

from gateway import VisioBASGateway
from gateway.utils import disable_loggers, get_file_logger

# from aiomisc.log import basic_config

BASE_DIR = Path(__file__).resolve().parent
GATEWAY_CFG_PATH = BASE_DIR / 'config/gateway.yaml'

# Set logging
LOG_FORMAT = os.environ.get('LOG_FORMAT',
                            '%(levelname)-8s [%(asctime)s] %(name)s'
                            '.%(funcName)s(%(lineno)d): %(message)s'
                            )
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
# _log = logging.getLogger(__name__)
_log = get_file_logger(__name__)

logging.basicConfig(format=LOG_FORMAT,
                    level=LOG_LEVEL,
                    stream=sys.stdout, )


# basic_config(level=logging.DEBUG, buffered=True, flush_interval=2,
#              # log_format=_log_fmt,
#              stream=sys.stderr
#              )

async def load_and_run(cfg_path: Path):
    gateway = VisioBASGateway.from_yaml(yaml_path=cfg_path)
    await gateway.async_run()


def main():
    unused_loggers = ('BAC0_Root.BAC0.scripts.Base.Base',
                      'BAC0_Root.BAC0.scripts.Lite.Lite',
                      'BAC0_Root.BAC0.tasks.UpdateCOV.Update_local_COV',
                      'BAC0_Root.BAC0.tasks.TaskManager.Manager',
                      'BAC0_Root.BAC0.tasks.RecurringTask.RecurringTask',
                      'bacpypes.iocb._statelog',
                      'bacpypes.task',

                      'pymodbus.client.sync',
                      'pymodbus.transaction',
                      'pymodbus.framer.socket_framer',
                      'pymodbus.factory',
                      'pymodbus.payload',)
    disable_loggers(loggers=unused_loggers)
    asyncio.run(load_and_run(cfg_path=GATEWAY_CFG_PATH),  # debug=True
                )


if __name__ == '__main__':
    main()
