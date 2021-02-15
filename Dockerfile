FROM python:3.9

LABEL maintainer="VisioBAS <info.visiobas.com>" description="VisioBAS Gateway"

RUN	mkdir -p /visiobas-gateway
COPY . /visiobas-gateway

WORKDIR /visiobas-gateway

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 502 1883 7070 8080 8883 47808 47809 47810 47811 47812 47813 47814 47815 47816 47817 47818 47819 47820 47821 47822 47823