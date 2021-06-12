from pathlib import Path

# from gateway.gateway_ import VisioBASGateway

"""VisioBAS IoT gateway."""

__version__ = '3.2.0'
__author__ = 'VisioBAS, Ovtsin Matvey'
__maintainer__ = __author__
__email__ = 'mtovtsin@gmail.com'
__url__ = '<info.visiobas.com>'
__license__ = 'GNU General Public License v3.0'

BASE_DIR = Path(__file__).resolve().parent

__all__ = [  # 'VisioBASGateway',

    '__author__',
    '__email__',
    '__license__',
    '__maintainer__',
    '__version__',

    'BASE_DIR',
]
