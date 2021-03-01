# https://docs.docker.com/develop/develop-images/multistage-build/#use-multi-stage-builds

############### Image for building a virtual environment ################
# Base - "heavy" image (~ 1 GB, compressed ~ 500 GB)
FROM python:3.9 as builder

# Create a virtual environment and update pip
RUN python3.9 -m venv /usr/share/python3/gw \
    && /usr/share/python3/gw/bin/pip install -U pip

# Install dependencies separately for caching
# On a subsequent build, Docker will skip this step if requirements.txt does not change
COPY requirements.txt /mnt/
RUN /usr/share/python3/gw/bin/pip install -Ur /mnt/requirements.txt

# Copy the source distribution to the container and install it
COPY /dist/ /mnt/dist/
RUN /usr/share/python3/gw/bin/pip install /mnt/dist/* \
    && /usr/share/python3/gw/bin/pip check


########################### Final image ############################
# Base - "lightweight" image (~ 100 MB, compressed ~ 50 MB)
FROM python:3.9-slim-buster as gateway

LABEL maintainer="VisioBAS <info.visiobas.com>" description="VisioBAS Gateway"

# IMPORTANT: the virtual environment uses absolute paths, so
# it must be copied to the same address,
# with which it was build in a building container.

# Copy the final virtual environment from the builder container
COPY --from=builder /usr/share/python3/gw /usr/share/python3/gw

# Install links to use gateway commands
RUN ln -snf /usr/share/python3/gw/bin/gateway  /usr/local/bin/

# Set the default command to run when the container starts
CMD ["gateway"]

EXPOSE 502 7070 8080 47808
