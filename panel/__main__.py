import logging
import sys
from logging import getLogger
from pathlib import Path

from aiomisc.log import basic_config

from panel import VisioPanel

_base_path = Path(__file__).resolve().parent

_log = getLogger(__name__)


def main():
    basic_config(level=logging.DEBUG, buffered=True, flush_interval=2,
                 # log_format=_log_fmt,
                 stream=sys.stderr
                 )

    panel = VisioPanel()
    panel.run_loop()


if __name__ == '__main__':
    main()

    # todo requirements and setup.py
