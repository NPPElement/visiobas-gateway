sudo docker-compose down
# todo cancel changes
# sudo git pull

cd ..
sudo rm -r visiobas-gateway
sudo git clone --single-branch --branch develop https://github.com/NPPElement/visiobas-gateway
cd visiobas-gateway/

# cp cfg from home/ todo

# todo: here set:
#  gateway/config/http.yaml
#  gateway/config/mqtt.yaml
#  gateway/connectors/bacnet/address_cache
#  gateway/connectors/modbus/address_cache

# Make changes now

sudo python3 setup.py sdist # create a source distribution

sudo docker-compose up --build
