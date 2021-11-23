from __future__ import print_function

import os
from pathlib import Path
import requests
import pip
import subprocess

UNAME_TYPE = subprocess.run(['uname', '-m'], capture_output=True).stdout.decode().strip('\n')
MACHINE_TYPE = subprocess.run(['dpkg', '--print-architecture'], capture_output=True).stdout.decode().strip('\n')

INSTALL_DIRECTORY = Path('/opt/visiobas-gateway')
INSTALL_DIRECTORY.mkdir(exist_ok=True)

CONFIG_DIRECTORY = (INSTALL_DIRECTORY / 'config')
CONFIG_DIRECTORY.mkdir(exist_ok=True)

DOCKER_COMPOSE_YAML_PATH = INSTALL_DIRECTORY / 'docker-compose.yaml'
ENV_CONFIG_PATH = CONFIG_DIRECTORY / '.env'


class Installer:
    DOCKER_CLIENT_DEPENDENCIES = [
        'apt-transport-https',
        'ca-certificates',
        'curl',
        'gnupg2',
        'software-properties-common',
    ]

    @staticmethod
    def important_msg(msg):
        print(
            '''
            ******************************
            %s
            ******************************
            ''' % msg
        )

    @staticmethod
    def run_cmd_with_check(cmd):
        code = os.system(cmd)
        if code:
            raise RuntimeError('Return code: %d for `%s`' % (code, cmd))

    @staticmethod
    def download_file(url, path):
        response = requests.get(url)
        if response.status_code == 200:
            path.write_bytes(response.content)
            # with open("DOCKER_COMPOSE_YAML", 'wb') as f:
            #     f.write()
        else:
            raise RuntimeError(
                'Cannot download `%s` HTTP code: %s' % (
                    DOCKER_COMPOSE_YAML_PATH, response.status_code
                )
            )

    def install_docker_engine(self):
        """
        Returns:
            Is installed successful.
        Raises:
            RuntimeError if return code any of cmd is not 0.
        """

        cmd = ' '.join(('apt-get -y install', *self.DOCKER_CLIENT_DEPENDENCIES))
        self.run_cmd_with_check(cmd)

        self.run_cmd_with_check(
            'curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -')
        if UNAME_TYPE == 'x86_64':
            self.run_cmd_with_check('add-apt-repository -y \
                   "deb [arch=amd64] https://download.docker.com/linux/debian \
                   $(lsb_release -cs) \
                   stable"')
        elif MACHINE_TYPE == 'armhf':
            self.run_cmd_with_check('add-apt-repository -y \
                   "deb [arch=armhf] https://download.docker.com/linux/debian \
                   $(lsb_release -cs) \
                   stable"')
        elif MACHINE_TYPE == 'arm64':
            self.run_cmd_with_check('add-apt-repository -y \
                   "deb [arch=arm64] https://download.docker.com/linux/debian \
                   $(lsb_release -cs) \
                   stable"')
        else:
            raise RuntimeError(
                'Could not detect architecture: uname=%s machinery=%s' % (
                    UNAME_TYPE, MACHINE_TYPE)
            )
        self.run_cmd_with_check('apt-get update')
        self.run_cmd_with_check('apt-get -y install docker-ce-cli')
        self.run_cmd_with_check('apt install -y docker-ce containerd.io')

    @staticmethod
    def install_docker_compose():
        pip.main(['install', 'docker-compose'])


if __name__ == '__main__':
    if os.geteuid() != 0:
        exit("Must be run as root.\n")

    installer = Installer()

    try:

        installer.run_cmd_with_check('apt-get update -y')

        print('Installing Docker engine')
        installer.install_docker_engine()

        print('Installing docker-compose')
        installer.install_docker_compose()

        print('All dependencies installed.')

        print('Downloading `%s`' % DOCKER_COMPOSE_YAML_PATH)
        installer.download_file(
            url="https://github.com/NPPElement/visiobas-gateway/tree/main/docker-compose.yaml",
            path=DOCKER_COMPOSE_YAML_PATH
        )

        print('Pulling docker image')
        installer.run_cmd_with_check('docker pull mtovts/visiobas-gateway:latest')

        print('Downloading `%s`' % ENV_CONFIG_PATH)
        installer.download_file(
            url="https://github.com/NPPElement/visiobas-gateway/tree/main/config/template.env",
            path=ENV_CONFIG_PATH
        )

        installer.important_msg(
            '''
            INSTALLATION COMPLETE
            ---------------------
            Please, configure gateway in` %s`
            Then run `docker-compose up`
            ''' % CONFIG_DIRECTORY
        )
    except Exception as exc:
        # TODO add traceback
        installer.important_msg(
            '''
            INSTALLATION FAILED
            -------------------
            Please contact to VisioBAS Gateway developers and provide this message:
            %s
            ''' % exc
        )
