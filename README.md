![GitHub tag (latest SemVer)](https://img.shields.io/github/v/tag/NPPElement/visiobas-gateway)
[![Run Checks](https://github.com/NPPElement/visiobas-gateway/actions/workflows/checks.yml/badge.svg)](/actions/workflows/checks.yml)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![License](https://img.shields.io/github/license/NPPElement/visiobas-gateway)](/LICENSE)

# VisioBAS-Gateway

Polling controllers on various protocols for
the [VisioBAS system](https://github.com/NPPElement/visiobas-broker).

### Contents

1. [Features](#Features)
2. [API](#API)
3. [Installation](#Installation)
4. [Setting](#Setting)
    - [Setting Serial ports](#Setting-Serial-ports)
    - [Setting configuration](#Setting-configuration)
5. [Launch/Update](#LaunchUpdate)
6. [Develop](#Develop)
7. [Remove](#Remove)

## Features

- Gateway provides the opportunity to poll devices from various vendors, using various
  protocols. Standardization based on `BACnet` protocol.
- Supported protocols: `BACnet`, `ModbusTCP`, `ModbusRTU`, `ModbusRTUoverTCP`
  , `SUNAPI`.
- Clients: `HTTP`, `MQTT`.
- `JSON-RPC 2.0 API` (over `HTTP` and `MQTT`) to control devices and request info about
  device.
- For processing events related to object's properties you can use verifier class.
- Devices and clients periodically updates.

## API

### `JSON-RPC 2.0 API` Available on `http://host:port/json-rpc`. Also you may use it by MQTT (provide topics for subscribe to use).

```shell
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"jsonrpc":"2.0","method":"writeSetPoint","params":{"device_id":"35","object_type":"2","object_id":"1","property":"85","priority":"10","index":"-1","tag":"9","value":"40"},"id":""}' \
  http://127.0.0.1:7070/json-rpc
```

## Installation

### a. [Install Docker](https://docs.docker.com/engine/install/)

### b. [Install Docker Compose](https://docs.docker.com/compose/install/)

### c. Install VisioBAS Gateway

```shell
cd /opt
sudo git clone https://github.com/NPPElement/visiobas-gateway
cd /opt/visiobas-gateway

# Configure visiobas_gateway now. Then:
. run/install.sh
```

## Setting

### Configuration

Application configures via environment variables. Environment variables are provided
via `.env` file. Paths to `.env` file are specified in `docker-compose.yaml`.

Configuration can be changed in file:

- `config/.env` [template](/config/template.env)


### Objects configuration

[/docs](/docs) contains JSON-schema definitions for used `pydantic` models. 

[~~/docs/properties.md~~](/docs/properties.md) (Outdated & will be removed soon).

### Setting Serial ports

```shell
sudo apt-get install minicom  # install minicom
dmesg | grep tty  # show ports
sudo minicom -s # launch minicom
# Setup serial ports from minicom, then save as dfl.

sudo nano /etc/udev/rules.d/99-serial.rules
# then write line: KERNEL=="ttyUSB[0-9]*",MODE="0666"

# Explanations: https://www.losant.com/blog/how-to-access-serial-devices-in-docker

# Before launch visiobas_gateway, ensure user in the `dialout` group
sudo usermod -a -G dialout username # add to `dialout` group
id username # check user\group info
```

## Launch/Update

To launch on the same machine
with [VisioBAS system](https://github.com/NPPElement/visiobas-broker) - add
in `docker-compose.yaml` the following network settings (commented now):

```yml
    networks:
      - backend
```

and

```yml
networks:
  backend: # your network name
    driver: bridge
```

Scripts for common actions available:

```shell
. run/logs_clear.sh  # Clear logs

. run/update.sh  # Git pull + build + launch
```

### Build and copy docker image
```shell
cd /opt/visiobas-gateway

docker build -t visiobas-gateway .

# docker save -o <path for generated tar file> <image name>
docker save -o /opt/gtw-latest-image.tar.gz visiobas-gateway:latest

# Copy via scp here
# Example: scp /opt/gtw-latest-image.tar.gz user@10.21.80.240:/opt

docker load -i <path to copied image file>
```

## Develop

### Setting up a Dev Environment

1. Make sure you have [Poetry](https://python-poetry.org/) installed and up to date.
2. Make sure you have a supported Python version (e.g. 3.9) installed and accessible to
   Poetry (e.g. with [pyenv](https://github.com/pyenv/pyenv).
3. Use `poetry install` in the project directory to create a virtual environment with the
   relevant dependencies.
4. Enter a `poetry shell` to make running commands easier.

### Writing Code

1. Write some code and make sure it's covered by unit tests. All unit tests are in
   the `tests` directory and the file structure should mirror the structure of the source
   code in the `visiobas_gateway` directory.
2. When in a Poetry shell (`poetry shell`) run `task check` in order to run most of the same
   checks CI runs. This will auto-reformat the code, check type annotations, run unit tests,
   check code coverage, and lint the code.
3. If writing support for a new protocol, regenerate the [/docs](/docs) with `task docs`. It
   will update JSON-schema definition for used `pydantic` models.

## Remove

To clean docker:

```shell
sudo docker-compose down 
sudo docker images

sudo docker rmi -f [image_id]
# OR
sudo docker images -a | xargs -n 1 -I {} sudo docker rmi -f {}
```

```shell
# Delete all containers
sudo docker ps -a -q | xargs -n 1 -I {} sudo docker rm -f {}

# Remove all unused images, not just dangling ones
sudo docker image prune -a -f

# If deleting or stopping the container is hopeless
sudo systemctl daemon-reload
sudo systemctl restart docker
```
