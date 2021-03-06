from json import loads, JSONDecodeError

import paho.mqtt.client as mqtt

from gateway.api.mixins import ReadWriteMixin, DevObjMixin, I2CRWMixin
from gateway.models import ObjProperty, ObjType


class VisioMQTTApi(DevObjMixin, ReadWriteMixin, I2CRWMixin):

    def __init__(self, visio_mqtt_client, gateway):
        self.mqtt_client = visio_mqtt_client
        self._gateway = gateway

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

    def rpc_value(self, params: dict, topic: str, gateway=None) -> None:
        if str(self._gateway) == 'VisioGateway':
            self.rpc_value_gw(params=params, gateway=gateway)
        elif str(self._gateway) == 'VisioPanel':
            self.rpc_value_panel(params=params, topic=topic)
        else:
            raise ValueError('Please provide gateway or panel')

    def rpc_value_panel(self, params: dict, topic: str) -> None:
        # todo: default value
        # todo: validate params
        publish_topic = topic.replace('Set', 'Site')

        if params['object_type'] == ObjType.BINARY_OUTPUT.id:
            _is_equal = self.write_with_check_i2c(value=params['value'],
                                                  obj_id=params['object_id'],
                                                  obj_type=params['object_type'],
                                                  dev_id=params['device_id']
                                                  )
            if not _is_equal:
                return None
            payload = '{0} {1} {2} {3}'.format(params['device_id'],
                                               params['object_type'],
                                               params['object_id'],
                                               params['value'],
                                               )

        elif params['object_type'] == ObjType.BINARY_INPUT.id:
            value = self.read_i2c(obj_id=params['object_id'],
                                  obj_type=params['object_type'],
                                  dev_id=params['device_id']
                                  )
            payload = '{0} {1} {2} {3}'.format(params['device_id'],
                                               params['object_type'],
                                               params['object_id'],
                                               value,
                                               )
        else:
            raise ValueError('Expected only BI or BO')
        self.publish(topic=publish_topic,
                     payload=payload,
                     )

    def rpc_value_gw(self, params: dict, gateway) -> None:
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
        self.publish(topic=obj.topic,  # todo: change topic here?
                     payload=payload,
                     )
