import argparse
import logging
import sys

from gateway.visio_gateway import VisioGateway

LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'


def main():
    # Setting the VisioGateway logging level
    # todo: change to logging level by param
    # level being 'DEBUG, INFO, WARNING, ERROR'
    
    # level = logging.DEBUG 
    # level = logging.INFO
    # level = logging.WARNING
    level = logging.ERROR

    logging.basicConfig(format=LOGGER_FORMAT,
                        level=level,
                        stream=sys.stdout)

    # Setting the BAC0 logging levels
    # BAC0.log_level('silence')

    VisioGateway()


if __name__ == '__main__':
    main()
