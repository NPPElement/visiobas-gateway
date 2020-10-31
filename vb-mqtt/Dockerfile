FROM debian:jessie
MAINTAINER VISIODAS, info.visiobas.com

# Install system requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    wget && \
    apt-get autoremove -y && \
    apt-get clean

# Configure locales and timezone
RUN locale-gen en_US.UTF-8 en_GB.UTF-8 fr_CH.UTF-8 && \
    cp /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    echo "Europe/Moscow" > /etc/timezone

# Install mosquitto clients
RUN apt-get update && apt-get install -y mosquitto-clients

EXPOSE 1883 8883 