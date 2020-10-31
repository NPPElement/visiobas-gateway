#!/bin/bash

while true
do
	D=$(date  +%Y-%m-%d)
	T=$(date +%H:%M:%S)

	mosquitto_pub -h 10.21.80.10 -t heartbeat -m "$D" "$T"

sleep 10
done