# Pull latest from github + build + launch

cd /opt/visiobas-gateway || { echo "Directory '/opt/visiobas-gateway' not found"; exit 1; }

sudo docker-compose down

sudo git pull || { echo "Uncommitted changes found. Please, commit them or use 'git stash'
."; exit 1; }

## Remove previous source distribution if exists
#sudo rm -r dist/

## sudo python3 setup.py sdist  # create a source distribution
#sudo ~/.poetry/bin/poetry build  # create a source distribution

## Export dependencies from Poetry to requirements.txt
#sudo sudo ~/.poetry/bin/poetry export -f requirements.txt --output requirements.txt

sudo docker-compose up --build # -d

echo '************************************'
echo '     VisioBAS Gateway started!'
echo '************************************'
