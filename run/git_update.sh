sudo docker-compose down
# todo cancel changes
sudo git pull

sudo python3 setup.py sdist  # create a source distribution

sudo docker-compose up --build
