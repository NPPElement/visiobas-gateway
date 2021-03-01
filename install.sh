# IMPORTANT: Without install git, python and docker now
# TODO

# fixme: clone main branch (current not released yet)
sudo git clone --single-branch --branch develop https://github.com/NPPElement/visiobas-gateway

# shellcheck disable=SC2164
cd visiobas-gateway/

# todo: here set:
#  gateway/config/http.yaml
#  gateway/config/mqtt.yaml
#  gateway/connectors/bacnet/address_cache
#  gateway/connectors/modbus/address_cache

# Configure docker-compose.yaml if need

sudo python3 setup.py sdist # create a source distribution
# if not creating - use current from /dist (problem was only in .240 server)
# fixme: solve sdist problem then remove

sudo docker-compose up --build




