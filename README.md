# VisioBAS-Gateway

Application for polling devices using various protocols and transmitting data to
the [VisioBAS system](https://github.com/NPPElement/visiobas-broker).

### Contents
0. [API](#API)
1. [Installation](#Installation)
    - [Install Docker](#--Install-Docker)
    - [Install Docker Compose](#--Install-Docker-Compose)
    - [Install VisioBAS gateway](#--Install-VisioBAS-Gateway)
2. [Setting](#Setting)
    - [Setting COM ports](#Setting-Serial-ports)
    - [Setting configuration](#Setting-configuration)
3. [Launch/Update](#LaunchUpdate)
4. [Remove](#Remove)
5. [License Information](#License-Information)

## API

### `JSON-RPC 2.0` API Available on `http://127.0.0.1:7070/json-rpc`.

### `REST API` Not support now.

~~Swagger docs available on http://127.0.0.1:7070/~~

```shell
# curl -X GET http://127.0.0.1:7070/api/v1/property/35/2/1/85

curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"jsonrpc":"2.0","method":"writeSetPoint","params":{"device_id":"35","object_type":"2","object_id":"1","property":"85","priority":"10","index":"-1","tag":"9","value":"40"},"id":""}' \
  http://127.0.0.1:7070/json-rpc
```

## Installation

### 1. [Install Docker](https://docs.docker.com/engine/install/)

### 2. [Install Docker Compose](https://docs.docker.com/compose/install/)

### 3. Install VisioBAS Gateway

```shell
cd /opt
sudo git clone https://github.com/NPPElement/visiobas-gateway
cd visiobas-gateway
```

## Setting

### Setting configuration

Configuration can be changed in files:
  - `docker-compose.yaml`
  - `gateway/config/gateway.env` [template](/gateway/config/templates/gateway.env)
  - `gateway/config/http.env` [template](/gateway/config/templates/http.env)
  - TODO: mqtt

### Logging level

- Logging level You can change the logging level in the `docker-compose.yaml` file. You can
  choose one of the following levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### [Objects configuration](/docs/properties_ru.md)

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

```shell
. run/logs_clear.sh  # Clear logs

. run/git_update.sh  # Git pull + build + launch
```

To clean docker:

```shell
sudo docker-compose down 
sudo docker images

sudo docker rmi -f [image_id]
# OR
sudo docker images -a | xargs -n 1 -I {} sudo docker rmi -f {}
```

## Remove

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
