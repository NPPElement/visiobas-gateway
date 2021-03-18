import logging
import os
import sys
from logging import getLogger
from pathlib import Path

from gateway.panel import VisioPanel

# from aiomisc.log import basic_config

_base_path = Path(__file__).resolve().parent

_log = getLogger(__name__)


def main():
    _log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
    _log_fmt = ('%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s'
                '.%(funcName)s(%(lineno)d): %(message)s'
                )
    # basic_config(level=logging.DEBUG, buffered=True, flush_interval=2,
    #              # log_format=_log_fmt,
    #              stream=sys.stderr
    #              )
    logging.basicConfig(level=_log_level,
                        format=_log_fmt,
                        stream=sys.stderr
                        )

    panel = VisioPanel()
    panel.run_loop()


if __name__ == '__main__':
    main()
