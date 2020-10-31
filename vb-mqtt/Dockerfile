FROM	alpine:3.12

LABEL 	maintainer="VisioBAS <info.visiobas.com>" \
		description="VisioBAS Mosquitto MQTT"

ENV 	LWS_VERSION=0.0.1

RUN		apt-get update && apt-get install -y --no-install-recommends \
		locales \
		wget && \
		apt-get autoremove -y && \
		apt-get clean

# Configure locales and timezone
RUN		locale-gen en_US.UTF-8 en_GB.UTF-8 fr_CH.UTF-8 && \
		cp /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
		echo "Europe/Moscow" > /etc/timezone \

# Install mosquitto clients	
RUN		apt-get update && apt-get install -y mosquitto-clients

# Directory for data and log
RUN		mkdir -p /mosquitto/data /mosquitto/log

WORKDIR	/mosquitto/

VOLUME	["/mosquitto/data", "/mosquitto/log"]

# TODO SSL 8883
EXPOSE 1883