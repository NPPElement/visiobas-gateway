from pathlib import Path

"""VisioBAS Gateway."""

__version__ = '3.2.4'
__author__ = 'VisioBAS, Matvey Ovtsin'
__maintainer__ = __author__
__email__ = 'mtovtsin@gmail.com'
__url__ = '<info.visiobas.com>'
__license__ = 'GNU General Public License v3.0'

BASE_DIR = Path(__file__).resolve().parent

__all__ = [
    '__author__',
    '__email__',
    '__license__',
    '__maintainer__',
    '__version__',

    'BASE_DIR',
]
