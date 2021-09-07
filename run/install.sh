# Updates packages
sudo apt --assume-yes update
sudo apt --assume-yes upgrade

# Install required applications
sudo apt --assume-yes install docker docker.io
sudo apt --assume-yes install htop mc curl
sudo apt --assume-yes install git
sudo apt --assume-yes install python3
sudo apt --assume-yes install python3-pip
sudo pip3 install setuptools

# Install docker-compose from VisioBAS Cloud
DESTINATION=/usr/bin/docker-compose
sudo curl -L https://289122.selcdn.ru/Visiodesk-Cloud/containers/docker-compose-Linux-x86_64 -o $DESTINATION
#VERSION=$(curl --silent https://api.github.com/repos/docker/compose/releases/latest | jq .name -r)
#sudo curl -L https://github.com/docker/compose/releases/download/${VERSION}/docker-compose-$(uname -s)-$(uname -m) -o $DESTINATION
#sudo curl -L https://github.com/docker/compose/releases/download/1.27.4/docker-compose-$(uname -s)-$(uname -m) -o $DESTINATION
sudo chmod 755 $DESTINATION
docker-compose --version

# Install Poetry
sudo curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

# Install gateway
cd /opt/visiobas-gateway
#sudo python3 setup.py sdist  # create a source distribution
sudo poetry build  # create a source distribution

# Copy configuration templates into /opt/visiobas-gateway/config
sudo cp /opt/visiobas-gateway/config/templates/gateway.env /opt/visiobas-gateway/config/gateway.env
sudo cp /opt/visiobas-gateway/config/templates/http.env /opt/visiobas-gateway/config/http.env
sudo cp /opt/visiobas-gateway/config/templates/mqtt.env /opt/visiobas-gateway/config/mqtt.env
sudo cp /opt/visiobas-gateway/config/templates/api.env /opt/visiobas-gateway/config/api.env

# Run container
sudo docker-compose up --build -d

echo '************************************'
echo '     VisioBAS Gateway started!'
echo '************************************'

