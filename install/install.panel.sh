# FIXME: IMPORTANT: ensure that Python 3.9.1 using

sudo git clone --single-branch --branch develop https://github.com/NPPElement/visiobas-gateway

cd visiobas-gateway/

# todo: here set:
#  panel/config/mqtt.yaml

export PYTHONPATH=./

sudo python3 setup.panel.py sdist # create a source distribution

# Create a virtual environment and update pip
sudo python3 -m venv pnl
sudo ./pnl/bin/pip install -U pip

# install source distribution
sudo ./pnl/bin/pip install -Ur requirements.panel.txt
sudo ./pnl/bin/pip install ./dist/visiobas-panel*

sudo python3 ./pnl/bin/panel
