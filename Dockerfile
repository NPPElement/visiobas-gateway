FROM python:3.9

WORKDIR /visiobas_gateway/

# Install Poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY ./pyproject.toml ./poetry.lock* /visiobas_gateway/

RUN bash -c poetry install

COPY ./visiobas_gateway /visiobas_gateway
EXPOSE 7070

RUN python /visiobas_gateway