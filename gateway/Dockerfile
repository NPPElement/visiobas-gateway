FROM python:3.9

LABEL maintainer="VisioBAS <info.visiobas.com>" \
 description="VisioBAS Gateway"

RUN	mkdir -p /vb_gateway
COPY . /vb_gateway

WORKDIR /

# VOLUME ["/gateway/config", "/gateway/logs", "/gateway/connectors/bacnet"]

# RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /vb_gateway/requirements.txt
# RUN pip install --no-cache-dir paho-mqtt

EXPOSE 502 1883 8080 8883 47808 47809 47810 47811 47812 47813 47814 47815 47816 47817 47818 47819 47820 47821 47822 47823