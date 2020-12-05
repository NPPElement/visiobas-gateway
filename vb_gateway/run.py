import logging
import os
# import paho.mqtt.client as mqtt
import sys

from vb_gateway.gateway.visio_gateway import VisioGateway

LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - ' \
                '(%(filename)s).%(funcName)s(%(lineno)d): %(message)s'


def main():
    # Setting the VisioGateway logging level
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(format=LOGGER_FORMAT,
                        level=log_level,
                        stream=sys.stdout)

    # Disable BAC0 loggers
    loggers_to_disable = (
        'BAC0_Root.BAC0.scripts.Base.Base',
        'BAC0_Root.BAC0.scripts.Lite.Lite',
        'BAC0_Root.BAC0.tasks.UpdateCOV.Update_local_COV',
        'BAC0_Root.BAC0.tasks.TaskManager.Manager',
        'BAC0_Root.BAC0.tasks.RecurringTask.RecurringTask',
        'bacpypes.iocb._statelog',
        'bacpypes.task'
    )
    for logger in loggers_to_disable:
        logging.getLogger(logger).setLevel(level=logging.CRITICAL)

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
