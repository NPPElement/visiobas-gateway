from json import loads, JSONDecodeError
from typing import Any

import paho.mqtt.client as mqtt

from gateway.api.mixins import ModbusRWMixin, DevObjMixin


class VisioMQTTApi(DevObjMixin, ModbusRWMixin):

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
        device = self.get_device(dev_id=params['device_id'],
                                 gateway=gateway
                                 )
        obj = self.get_obj(device=device,
                           obj_type=params['object_type'],
                           obj_id=params['object_identifier']
                           )
        self.write_modbus(value=params['value'],
                          obj=obj,
                          device=device
                          )
        cur_value = self.read_modbus(obj=obj,
                                     device=device
                                     )
        sf = 0b0000  # fixme
        payload = '{0} {1} {2} {3} {4}'.format(device.id,
                                               obj.type,
                                               obj.id,
                                               cur_value,
                                               sf
                                               )
        _ = self.publish(topic=obj.topic,
                         payload=payload,
                         )
