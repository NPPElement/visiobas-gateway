# import os
# from importlib.machinery import SourceFileLoader
#
# from pkg_resources import parse_requirements
from setuptools import find_packages, setup

# from gateway import __version__, __author__, __email__, __license__

# module_name = 'visiobas_gateway'
#
# # The module may not be installed yet (or a different version is installed), so
# # need to load __init__.py with machinery.
# module = SourceFileLoader(
#     module_name, os.path.join(module_name, '__init__.py')
# ).load_module()
#
#
# def load_requirements(fname: str) -> list[str]:
#     requirements = []
#     with open(fname, 'r') as fp:
#         for req in parse_requirements(fp.read()):
#             extras = '[{}]'.format(','.join(req.extras)) if req.extras else ''
#             requirements.append(
#                 '{}{}{}'.format(req.name, extras, req.specifier)
#             )
#     return requirements


setup(name='visiobas-gateway',
      version='0.1.3',
      author='VisioBAS, Ovtsin Matvey',
      # author_email=__email__,
      # license=__license__,
      description='VisiBAS IoT gateway.',
      # long_description=open('README.md').read(),
      url='https://github.com/NPPElement/visiobas-gateway',
      # platforms='all',
      classifiers=['Programming Language :: Python',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.9',
                   'Programming Language :: Python :: Implementation :: CPython'
                   ],
      python_requires='>=3.9',
      packages=find_packages(exclude=['tests']),
      # install_requires=load_requirements('requirements.txt'),
      install_requires=['aiohttp==3.7.3',
                        'BAC0==21.2.5',
                        'bacpypes==0.18.3',
                        'pymodbus==2.4.0',
                        'paho-mqtt~=1.5.1',
                        'aiomisc~=11.1.11',
                        # 'setuptools~=53.0.0',
                        'marshmallow~=3.10.0',
                        'PyYAML==5.4.1',
                        'netifaces==0.10.9',
                        'aiohttp-apispec==2.2.1',
                        ],
      # extras_require={'dev': load_requirements('requirements.dev.txt')},
      entry_points={'console_scripts': ['gateway = gateway.__main__:main'
                                        ]
                    },
      include_package_data=True
      )
