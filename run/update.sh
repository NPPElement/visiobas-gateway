# Pull latest from github + build + launch

cd /opt/visiobas-gateway

sudo docker-compose down

sudo git pull

sudo rm -r dist/  # remove previous source distribution if exists
sudo python3 setup.py sdist  # create a source distribution

sudo docker-compose up --build # -d

#echo '************************************'
#echo '     VisioBAS Gateway started!'
#echo '************************************'
