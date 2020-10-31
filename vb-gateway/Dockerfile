FROM python:3.8.5-slim-buster

LABEL maintainer="VisioBAS <info.visiobas.com>" \
 description="VisioBAS Gateway"

RUN	mkdir -p /gateway

COPY . /gateway/

WORKDIR /gateway/

VOLUME ["/gateway/config", "/gateway/logs"]

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080 47808 47809 47810 47811 47812 47813 47814 47815 47816 47817 47818 47819 47820 47821 47822 47823