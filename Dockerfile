FROM python:3.9.9-slim-buster

WORKDIR /visiobas_gateway/

# Install ping
RUN apt-get update && apt-get install -y iputils-ping

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy poetry.lock* in case it doesn't exist in the repo
COPY ./pyproject.toml ./poetry.lock* /visiobas_gateway/

RUN poetry install --no-dev

COPY ./visiobas_gateway /visiobas_gateway
EXPOSE 7070
ENV PYTHONPATH=/visiobas_gateway

CMD ["python", "/visiobas_gateway"]