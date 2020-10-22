# Visiobas-Gateway

It is an application for polling devices using various protocols and transmitting data to the visiobas system.

## Installation

## Setting
To configure it, you need to edit the file visiobas_gateway/config/gateway.json

## Launch
Go to the visiobas-gateway directory
<pre>
sudo docker-compose up
</pre>

## Update
<pre>
sudo docker-compose down
</pre>
<pre>
sudo docker images
</pre>
<pre>
sudo docker rmi [id] 
</pre>
Set the data received after executing the previous command instead of the id
<pre>
sudo git pull
</pre>
<pre>
sudo docker-compose up
</pre>

## Level
You can change the logging level using visiobas_gateway/run.py
level being 'DEBUG, INFO, WARNING, ERROR'

## License
GPL-3.0 License
