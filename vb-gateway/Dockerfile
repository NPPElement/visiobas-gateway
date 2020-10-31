FROM python:3.9-Debian-buster

LABEL maintainer="VisioBAS <info.visiobas.com>" \
 description="VisioBAS Gateway"

RUN	mkdir -p /gateway

COPY . /gateway/

WORKDIR /gateway/

# VOLUME ["/gateway/config", "/gateway/logs", "/gateway/connectors/bacnet"]

# RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install packages
RUN sudo apt install mosquitto-clients

EXPOSE 8883 1883 8080 47808 47809 47810 47811 47812 47813 47814 47815 47816 47817 47818 47819 47820 47821 47822 47823