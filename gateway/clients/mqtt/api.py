from json import loads, JSONDecodeError
from typing import Any

import paho.mqtt.client as mqtt

from gateway.api.mixins import ReadWriteMixin, DevObjMixin
from gateway.models import ObjProperty


class VisioMQTTApi(DevObjMixin, ReadWriteMixin):

    def __init__(self, visio_mqtt_client):
        self.mqtt_client = visio_mqtt_client

    def publish(self, topic: str, payload: str = None, qos: int = 0,
                retain: bool = False) -> mqtt.MQTTMessageInfo:
        return self.mqtt_client.publish(topic=topic,
                                        payload=payload,
                                        qos=qos,
                                        retain=retain
                                        )

    @staticmethod
    def decode(msg: mqtt.MQTTMessage):
        try:
            if isinstance(msg.payload, bytes):
                content = loads(msg.payload.decode("utf-8", "ignore"))
            else:
                content = loads(msg.payload)
        except JSONDecodeError:
            if isinstance(msg.payload, bytes):
                content = msg.payload.decode("utf-8", "ignore")
            else:
                content = msg.payload
        return content

    def rpc_value(self, params: dict, gateway) -> Any:
        priority = 11 if params.get('priority') is None else params['priority']

        device = self.get_device(dev_id=params['device_id'],
                                 gateway=gateway
                                 )
        obj = self.get_obj(device=device,
                           obj_type=params['object_type'],
                           obj_id=params['object_identifier']
                           )
        self.write(value=params['value'],
                   obj=obj,
                   device=device,
                   priority=priority,
                   prop=ObjProperty.presentValue
                   )
        cur_value = self.read(obj=obj,
                              device=device,
                              prop=ObjProperty.presentValue
                              )
        sf = 0b0000  # fixme
        payload = '{0} {1} {2} {3} {4}'.format(device.id,
                                               obj.type,
                                               obj.id,
                                               cur_value,
                                               sf
                                               )
        self.publish(topic=obj.topic,
                     payload=payload,
                     )
