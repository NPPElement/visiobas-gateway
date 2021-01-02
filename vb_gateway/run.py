import logging
import os
import sys

from vb_gateway.gateway.visio_gateway import VisioGateway
from vb_gateway.logs import disable_loggers
from vb_gateway.utils.for_test import get_test_cfg
# from vb_gateway.utils import read_cfg_from_env

# Setting the VisioGateway logging level
_LOGGER_FORMAT = ('%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - '
                  '(%(filename)s).%(funcName)s(%(lineno)d): %(message)s')

_log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
_log = logging.getLogger(__name__)
_unused_loggers = (
    'BAC0_Root.BAC0.scripts.Base.Base',
    'BAC0_Root.BAC0.scripts.Lite.Lite',
    'BAC0_Root.BAC0.tasks.UpdateCOV.Update_local_COV',
    'BAC0_Root.BAC0.tasks.TaskManager.Manager',
    'BAC0_Root.BAC0.tasks.RecurringTask.RecurringTask',
    'bacpypes.iocb._statelog',
    'bacpypes.task'
)
logging.basicConfig(format=_LOGGER_FORMAT,
                    level=_log_level,
                    stream=sys.stdout,
                    )
disable_loggers(loggers=_unused_loggers)


def main():
    # config = read_cfg_from_env()
    config = get_test_cfg()

    VisioGateway(config=config)


if __name__ == '__main__':
    main()
