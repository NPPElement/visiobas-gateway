#!/bin/bash

# To install visiobas-gateway run:
# curl -sSL https://raw.githubusercontent.com/NPPElement/visiobas-gateway/main/run/install.sh | bash -

if [ "$EUID" -ne 0 ]; then
    printf "Must be run as root.\n"
    exit 1
fi

VISIOBAS_GATEWAY_PATH="/opt/visiobas-gateway"

apt-get update -y
apt-get upgrade -y
apt-get dist-upgrade -y
apt-get autoremove -y
apt-get install -y python3 python3-pip python3-dev python3-venv python3-setuptools libffi-dev libssl-dev curl
python3 -m pip install --upgrade pip

PYTHON_BINARY_SYS_LOC="$(python3 -c "import os; print(os.environ['_'])")"

# Creating virtual environment
python3 -m pip install virtualenv
python3 -m virtualenv --system-site-packages -p "${PYTHON_BINARY_SYS_LOC}" "${VISIOBAS_GATEWAY_PATH}"/.venv

curl -sSL https://raw.githubusercontent.com/NPPElement/visiobas-gateway/main/run/gtw_installer.py -o /opt/gtw_installer.py
python3 /opt/gtw_installer.py -h


# Install docker-compose from VisioBAS Cloud
#DESTINATION=/usr/bin/docker-compose
#sudo curl -L https://289122.selcdn.ru/Visiodesk-Cloud/containers/docker-compose-Linux-x86_64 -o $DESTINATION
##VERSION=$(curl --silent https://api.github.com/repos/docker/compose/releases/latest | jq .name -r)
##sudo curl -L https://github.com/docker/compose/releases/download/${VERSION}/docker-compose-$(uname -s)-$(uname -m) -o $DESTINATION
##sudo curl -L https://github.com/docker/compose/releases/download/1.27.4/docker-compose-$(uname -s)-$(uname -m) -o $DESTINATION
#sudo chmod 755 $DESTINATION
#docker-compose --version

# Install Poetry
# OUTDATED CMD HAS BEEN REMOVED

# Install visiobas_gateway
#cd /opt/visiobas-gateway
#sudo python3 setup.py sdist  # create a source distribution
#sudo ~/.poetry/bin/poetry build  # create a source distribution

# Export dependencies from Poetry to requirements.txt
# sudo sudo ~/.poetry/bin/poetry export -f requirements.txt --output requirements.txt
#  --without-hashes
