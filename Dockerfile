FROM python:3.8.5

RUN mkdir -p /usr/scr/gateway/
WORKDIR /usr/scr/gateway/

COPY . /usr/scr/gateway/
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080 47808

CMD ["python", "visiobas_gateway/run.py"]