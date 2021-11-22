from __future__ import print_function

import os

UNAME_TYPE = os.system('uname -m')
MACHINE_TYPE = os.system('dpkg --print-architecture')

def _exec_cmd(cmd):
    code = os.system(cmd)
    if code:
        raise RuntimeError('Code: %d %s' % (code, cmd))


def update():
    UPDATE_CMDS = [
        'apt-get update -y',
        'apt-get install -y python3 python3-dev python3-setuptools libssl-dev',
        '/usr/lib/python3/dist-packages/easy_install.py pip',
        'python3 -m pip install --upgrade pip'
    ]

    for cmd in UPDATE_CMDS:
        _exec_cmd(cmd=cmd)


def install_docker_client():
    DOCKER_CLIENT_DEPENDENCIES = [
        'apt-transport-https',
        'ca-certificates',
        'curl',
        'gnupg2',
        'software-properties-common',
    ]

    cmd = ' '.join(('apt-get -y install', *DOCKER_CLIENT_DEPENDENCIES))
    _exec_cmd(cmd)

    _exec_cmd('curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -')
    if UNAME_TYPE == 'x86_64':
        _exec_cmd('add-apt-repository -y \
               "deb [arch=amd64] https://download.docker.com/linux/debian \
               $(lsb_release -cs) \
               stable"')
    elif MACHINE_TYPE == 'armhf':
        _exec_cmd('add-apt-repository -y \
               "deb [arch=armhf] https://download.docker.com/linux/debian \
               $(lsb_release -cs) \
               stable"')
    elif MACHINE_TYPE == 'arm64':
        _exec_cmd('add-apt-repository -y \
               "deb [arch=arm64] https://download.docker.com/linux/debian \
               $(lsb_release -cs) \
               stable"')
    else:
        exit('Could not detect architecture.')
    _exec_cmd('apt-get update')
    _exec_cmd('apt-get -y install docker-ce-cli')


if __name__ == '__main__':
    if os.geteuid() != 0:
        exit("Please run as root.")

    _exec_cmd('apt-get update -y')

    print('Installing Docker client')
    install_docker_client()
    _exec_cmd('apt install -y docker-ce containerd.io')

    print('Installing docker-compose')
    _exec_cmd('python3 -m pip install docker-compose')

    print('All dependencies installed.')

    _exec_cmd('docker pull mtovts/visiobas-gateway:latest')

