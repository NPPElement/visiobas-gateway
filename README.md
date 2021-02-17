curl -X GET http://127.0.0.1:7070/api/property/35/2/1/2

curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"jsonrpc":"2.0","method":"writeSetPoint","params":{"device_id":"35","object_type":"2","object_id":"1","property":"85","priority":"10","index":"-1","tag":"9","value":"40"},"id":""}' \
  http://127.0.0.1:7070/json-rpc




# Visiobas-Gateway

It is an application for polling devices using various protocols and transmitting data to the visiobas system.


# API
Swagger docs available on http://127.0.0.1:7070/

```
curl -X GET http://127.0.0.1:7070/api/property/35/2/1/2
```

```
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"jsonrpc":"2.0","method":"writeSetPoint","params":{"device_id":"35","object_type":"2","object_id":"1","property":"85","priority":"10","index":"-1","tag":"9","value":"40"},"id":""}' \
  http://127.0.0.1:7070/json-rpc
```

## Installation

#### For install developing branch:
```
sudo git clone --single-branch --branch develop https://github.com/NPPElement/visiobas-gateway
```
### Install Docker
```
sudo apt update
```

```
sudo apt install apt-transport-https ca-certificates curl software-properties-common
```

```
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
```

```
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
```

```
sudo apt update
```

```
apt-cache policy docker-ce
```

```
sudo apt install docker-ce
```

```
sudo systemctl status docker
```

### - Install Docker Compose
```
sudo curl -L https://github.com/docker/compose/releases/download/1.21.2/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
```

```
sudo chmod +x /usr/local/bin/docker-compose
```
```
docker-compose --version
```

### - Install Visiobas Gateway
```
cd /opt
```
```
sudo git clone https://github.com/NPPElement/visiobas-gateway
```
```
cd visiobas-gateway
```

## Setting
Configuration can be changed in files `config/http.yaml` and `config/gateway.yaml`.

For `config/http.yaml` a fill template is available: `config/template-http.yaml`.


## Launch
Go to the `visiobas-gateway` directory
```
sudo docker-compose up -d
```
For enable docker logs:
```
sudo docker-compose logs -f
```

## Update
```
sudo docker-compose down
```
```
sudo docker-compose build
```
```
sudo docker-compose up
```

Or with full cleaning
```
sudo docker-compose down 
```
```
sudo docker images
```
```
sudo docker rmi -f [image_id]
```
OR
```
sudo docker images -a | xargs -n 1 -I {} sudo docker rmi -f {}
```

Set the data received after executing the previous command instead of the id
```
sudo git pull
sudo docker-compose up --build
```

## Remove
Delete all containers
```
sudo docker ps -a -q | xargs -n 1 -I {} sudo docker rm -f {}
```
Remove all unused images, not just dangling ones
```
sudo docker image prune -a -f
```
If deleting or stopping the container is hopeless
```
sudo systemctl daemon-reload
sudo systemctl restart docker
```

## Logging level
The logging level can be changed in the `docker-compose.yaml` file.

The following levels can be specified: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## License
GPL-3.0 License
