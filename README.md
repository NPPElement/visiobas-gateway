# VisioBAS-Gateway

Application for polling devices using various protocols and transmitting data to
the [VisioBAS system](https://github.com/NPPElement/visiobas-broker).

### Contents

0. [API](#API)
1. [Installation](#Installation)
    - [Install Docker](#a-Install-Docker)
    - [Install Docker Compose](#b-Install-Docker-Compose)
    - [Install VisioBAS gateway](#c-Install-VisioBAS-Gateway)
2. [Setting](#Setting)
    - [Setting COM ports](#Setting-Serial-ports)
    - [Setting configuration](#Setting-configuration)
3. [Launch/Update](#LaunchUpdate)
4. [Remove](#Remove)
5. [License Information](#License-Information)

## API

### `JSON-RPC 2.0` API Available on `http://host:port/json-rpc`.

~~Swagger docs available on http://host:port/~~ TODO: update

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

# Configure gateway now. Then:
. run/install.sh
```

## Setting

### Configuration

Application configures via environment variables. Environment variables are provided via `.env` files. Paths to `.env` files
are specified in `docker-compose.yaml`.

Configuration can be changed in files:

- `config/gateway.env` [template](/config/templates/gateway.env)
- `config/http.env` [template](/config/templates/http.env)
- `config/mqtt.env` [template](/config/templates/mqtt.env)
- `config/api.env` [template](/config/templates/api.env)

### Logging level

- Logging level You can change the logging level in the `docker-compose.yaml` file. You can choose one of the following
  levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Objects configuration

To configure objects properties read [this note](/docs/properties_ru.md).

### Setting Serial ports

```shell
sudo apt-get install minicom  # install minicom
dmesg | grep tty  # show ports
sudo minicom -s # launch minicom
# Setup serial ports from minicom, then save as dfl.

sudo nano /etc/udev/rules.d/99-serial.rules
# then write line: KERNEL=="ttyUSB[0-9]*",MODE="0666"

# Explanations: https://www.losant.com/blog/how-to-access-serial-devices-in-docker

# Before launch gateway, ensure user in the `dialout` group
sudo usermod -a -G dialout username # add to `dialout` group
id username # check user\group info
```

## Launch/Update

To launch on the same machine with [VisioBAS system](https://github.com/NPPElement/visiobas-broker) - add
in `docker-compose.yaml` the following network settings (commented now):

```yaml
networks:
  default:
    external: true
    name: services_backend  # or your network name
```

Scripts for common actions available:

```shell
. run/logs_clear.sh  # Clear logs

. run/update.sh  # Git pull + build + launch
```

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

### [License Information](/LICENSE)

`GPL-3.0 License`
