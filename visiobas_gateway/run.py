import argparse
import logging
import sys

from visiobas_gateway.gateway.visio_gateway import VisioGateway

LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] %(name)s: %(message)s'


def main():
    parser = argparse.ArgumentParser(
        description='Polling devices and sends data to server.')

    parser.add_argument('-d', '--debug', action='store_true', help='Enable detailed logs.')
    args = parser.parse_args()

    # Setting the VisioGateway logging level
    # todo: change to logging level by param
    # level = logging.DEBUG if args.debug else logging.INFO
    level = logging.INFO
    logging.basicConfig(format=LOGGER_FORMAT,
                        level=level,
                        stream=sys.stdout)

    # Setting the BAC0 logging levels
    # BAC0.log_level('silence')

    VisioGateway()


if __name__ == '__main__':
    main()
