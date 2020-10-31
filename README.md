# Visiobas-Gateway

It is an application for polling devices using various protocols and transmitting data to the visiobas system.

## Installation
### - Install Docker
<pre>
sudo apt update
</pre>
<pre>
sudo apt install apt-transport-https ca-certificates curl software-properties-common
</pre>
<pre>
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
</pre>
<pre>
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
</pre>
<pre>
sudo apt update
</pre>
<pre>
apt-cache policy docker-ce
</pre>
<pre>
sudo apt install docker-ce
</pre>
<pre>
sudo systemctl status docker
</pre>

### - Install Docker Compose
<pre>
sudo curl -L https://github.com/docker/compose/releases/download/1.21.2/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
</pre>
<pre>
sudo chmod +x /usr/local/bin/docker-compose
</pre>
<pre>
docker-compose --version
</pre>

### - Install Visiobas Gateway
<pre>
cd /opt
</pre>
<pre>
sudo git clone https://github.com/NPPElement/visiobas-gateway
</pre>
<pre>
cd visiobas-gateway
</pre>

## Setting
To configure it, you need to edit the file visiobas_gateway/config/gateway.json

## Launch
Go to the visiobas-gateway directory
<pre>
sudo docker-compose up -d
</pre>
For enable docker logs:
<pre>
sudo docker-compose logs -f
</pre>

## Update
<pre>
sudo docker-compose down
</pre>
<pre>
sudo docker-compose build
</pre>
<pre>
sudo docker-compose up --build
</pre>

Or with full cleaning
<pre>
sudo docker-compose down
</pre>
<pre>
sudo docker images
</pre>
<pre>
sudo docker rmi -f [image_id]
</pre>
Set the data received after executing the previous command instead of the id
<pre>
sudo git pull
</pre>
<pre>
sudo docker-compose build
</pre>
<pre>
sudo docker-compose up
</pre>

## Remove
Delete all containers
<pre>
sudo docker ps -a -q | xargs -n 1 -I {} sudo docker rm {}
</pre>
Remove all unused images, not just dangling ones
<pre>
sudo docker image prune -a -f
</pre>

## Level
You can change the logging level using visiobas_gateway/run.py
level being 'DEBUG, INFO, WARNING, ERROR'

## License
GPL-3.0 License
