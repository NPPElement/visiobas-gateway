# Visiobas-Gateway

It is an application for polling devices using various protocols and transmitting data to the visiobas system.


# API
Swagger docs available on http://127.0.0.1:7070/

```
curl -X GET http://127.0.0.1:7070/api/v1/property/35/2/1/85
```

```
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"jsonrpc":"2.0","method":"writeSetPoint","params":{"device_id":"35","object_type":"2","object_id":"1","property":"85","priority":"10","index":"-1","tag":"9","value":"40"},"id":""}' \
  http://127.0.0.1:7070/json-rpc
```

## Installation

### - [Install Docker](https://docs.docker.com/engine/install/)

### - [Install Docker Compose](https://docs.docker.com/compose/install/)

### - Install Visiobas Gateway
``` shell
cd /opt
sudo git clone https://github.com/NPPElement/visiobas-gateway
cd visiobas-gateway
```

## Setting
Configuration can be changed in files `gateway/config/gateway.env` and `gateway/config/http.env`.
Templates are available: `gateway/config/templates`.


## Launch/Update
``` shell
. run/clear_logs.sh  # Clear logs

. run/git_update.sh  # Git pull + build + run
```

To clean docker:
``` shell
sudo docker-compose down 
sudo docker images

sudo docker rmi -f [image_id]
# OR
sudo docker images -a | xargs -n 1 -I {} sudo docker rmi -f {}
```

## Remove
``` shell
# Delete all containers
sudo docker ps -a -q | xargs -n 1 -I {} sudo docker rm -f {}

# Remove all unused images, not just dangling ones
sudo docker image prune -a -f

# If deleting or stopping the container is hopeless
sudo systemctl daemon-reload
sudo systemctl restart docker
```

## Logging level
The logging level can be changed in the `docker-compose.yaml` file.

The following levels can be specified: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

## License
GPL-3.0 License
