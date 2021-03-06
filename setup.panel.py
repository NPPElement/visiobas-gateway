from pathlib import Path

from pkg_resources import parse_requirements
from setuptools import find_packages, setup

_req_path = Path().cwd() / 'requirements.panel.txt'
requirements = [str(r) for r in parse_requirements(_req_path.read_text())]


setup(name='visiobas-panel',
      version='0.1.5',
      author='VisioBAS, Ovtsin Matvey',
      # author_email=__email__,
      license='GNU General Public License v3.0',
      description='VisiBAS IoT panel.',
      long_description=open('README.md').read(),
      url='https://github.com/NPPElement/visiobas-gateway',
      # platforms='all',
      classifiers=['Programming Language :: Python',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.9',
                   'Programming Language :: Python :: Implementation :: CPython'
                   ],
      python_requires='>=3.9',
      packages=find_packages(exclude=['tests', 'gateway']),
      install_requires=requirements,
      # extras_require={'dev': load_requirements('requirements.dev.txt')},
      entry_points={'console_scripts': ['panel = panel.__main__:main'
                                        ]
                    },
      include_package_data=True
      )
