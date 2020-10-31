#!/bin/bash

while true
do
	
mosquitto_pub -h 10.21.80.10 -t heartbeat -m ok

sleep 10
done