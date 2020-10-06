import logging
import sys

from visiobas_gateway.gateway.visio_gateway import VisioGateway

logging.basicConfig(format='%(levelname)-8s [%(asctime)s] %(name)s: %(message)s',
                    level=logging.DEBUG, stream=sys.stdout)


def main():
    VisioGateway()


if __name__ == '__main__':
    main()
