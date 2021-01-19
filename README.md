# Visiobas-Gateway

It is an application for polling devices using various protocols and transmitting data to the visiobas system.

## Installation
### - Install Docker
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
To configure it, you need to edit the file `docker-compose.yaml`.
HTTP's settings must be specified in the `http_config.env`.
HTTP's settings file template [here](https://github.com/NPPElement/visiobas-gateway/blob/develop/http_config.env.template).


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
sudo docker-compose up -d
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

## Level
You can change the logging level in the `docker-compose.yaml` file.
You can choose one of the following levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## License
GPL-3.0 License
