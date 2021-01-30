import logging
import os
import sys

from gateway import VisioGateway
from gateway.logs import disable_loggers
from gateway.utils import read_cfg_from_env

# Setting the VisioGateway logging level
_log_fmt = ('%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - '
            '(%(filename)s).%(funcName)s(%(lineno)d): %(message)s'
            )
_log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
_log = logging.getLogger(__name__)
_unused_loggers = ('BAC0_Root.BAC0.scripts.Base.Base',
                   'BAC0_Root.BAC0.scripts.Lite.Lite',
                   'BAC0_Root.BAC0.tasks.UpdateCOV.Update_local_COV',
                   'BAC0_Root.BAC0.tasks.TaskManager.Manager',
                   'BAC0_Root.BAC0.tasks.RecurringTask.RecurringTask',
                   'bacpypes.iocb._statelog',
                   'bacpypes.task'
                   )
logging.basicConfig(format=_log_fmt,
                    level=_log_level,
                    stream=sys.stdout,
                    )
disable_loggers(loggers=_unused_loggers)


def main():
    config = read_cfg_from_env()
    VisioGateway(config=config)


if __name__ == '__main__':
    main()
