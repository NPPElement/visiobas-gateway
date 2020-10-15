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

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format=LOGGER_FORMAT,
                        level=level, stream=sys.stdout)

    VisioGateway()


if __name__ == '__main__':
    main()
