FROM python:3.9

LABEL maintainer="VisioBAS <info.visiobas.com>" \
 description="VisioBAS Gateway"

RUN	mkdir -p /gateway

COPY . /gateway/

WORKDIR /gateway/

# VOLUME ["/gateway/config", "/gateway/logs", "/gateway/connectors/bacnet"]

# RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install system requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    wget && \
    apt-get autoremove -y && \
    apt-get clean

# Install mosquitto clients
RUN wget -q -O /tmp/mosquitto-repo.gpg.key http://repo.mosquitto.org/debian/mosquitto-repo.gpg.key && \
    apt-key add /tmp/mosquitto-repo.gpg.key && \
    wget -q -O /etc/apt/sources.list.d/mosquitto-jessie.list http://repo.mosquitto.org/debian/mosquitto-jessie.list && \
    apt-get update && apt-get install -y mosquitto-clients

EXPOSE 8883 1883 8080 47808 47809 47810 47811 47812 47813 47814 47815 47816 47817 47818 47819 47820 47821 47822 47823