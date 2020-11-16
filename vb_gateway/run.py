import argparse
import logging
import sys
# import paho.mqtt.client as mqtt

from vb_gateway.gateway.visio_gateway import VisioGateway

LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'


def main():
    # Setting the VisioGateway logging level
    # todo: change to logging level by param
    # level being 'DEBUG, INFO, WARNING, ERROR'
    
    # level = logging.DEBUG 
    # level = logging.INFO
    # level = logging.WARNING
    level = logging.DEBUG

    logging.basicConfig(format=LOGGER_FORMAT,
                        level=level,
                        stream=sys.stdout)

    # Setting the BAC0 logging levels
    # BAC0.log_level('silence')

    # The callback for when the client receives a CONNACK response from the server.

    # def on_connect(client, userdata, rc):
    # print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")

    # The callback for when a PUBLISH message is received from the server.
    # def on_message(client, userdata, msg):
    #     print(msg.topic+" "+str(msg.payload))
    #
    #
    # client = mqtt.Client()
    # #client.on_connect = on_connect
    # client.on_message = on_message
    #
    # #client.connect("10.21.80.10", 1883, 60)
    # client.message("10.21.80.10", heartbeat, ok)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    # client.loop_forever()

    VisioGateway()


if __name__ == '__main__':
    main()
