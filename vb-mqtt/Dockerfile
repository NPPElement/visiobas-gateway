FROM alpine:3.12

LABEL maintainer="VisioBAS <info.visiobas.com>" \
 description="VisioBAS Mosquitto MQTT"

ENV LWS_VERSION=0.0.1

# Install packages
RUN apk --no-cache add mosquitto-clients

# Expose MQTT port
# TODO SSL 8883
EXPOSE 1883