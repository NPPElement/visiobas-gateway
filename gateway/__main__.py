import logging
import os
import sys
from pathlib import Path

from gateway import VisioBASGateway
from gateway.utils import disable_loggers

# from aiomisc.log import basic_config

_base_path = Path(__file__).resolve().parent


def main():
    # Set logging
    _log_fmt = ('%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s'
                '.%(funcName)s(%(lineno)d): %(message)s'
                )
    _log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
    _log = logging.getLogger(__name__)
    _unused_loggers = ('BAC0_Root.BAC0.scripts.Base.Base',
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
                       'pymodbus.payload'
                       )
    # logging.basicConfig(format=_log_fmt,
    #                     level=_log_level,
    #                     stream=sys.stdout,
    #                     )

    # basic_config(level=logging.DEBUG, buffered=True, flush_interval=2,
    #              # log_format=_log_fmt,
    #              stream=sys.stderr
    #              )

    disable_loggers(loggers=_unused_loggers)
    VisioBASGateway.from_yaml(yaml_path=_base_path / 'config/gateway.yaml').run()


if __name__ == '__main__':
    main()
