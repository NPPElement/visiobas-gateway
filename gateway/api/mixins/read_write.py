from typing import Any

from .bacnet_rw import BACnetRWMixin
from .modbus_rw import ModbusRWMixin
from ...connectors import BACnetDevice, ModbusDevice
from ...models import BACnetObj, ModbusObj, ObjProperty


class ReadWriteMixin(BACnetRWMixin, ModbusRWMixin):

    def read(
            self,
            obj: BACnetObj or ModbusObj,
            device: BACnetDevice or ModbusDevice,
            prop: ObjProperty = ObjProperty.presentValue
    ) -> Any:
        if isinstance(device, BACnetDevice):
            protocol_read_func = self.read_bacnet
        elif isinstance(device, ModbusDevice):
            protocol_read_func = self.read_modbus
        else:
            raise NotImplementedError('Only BACnet, Modbus implemented. '
                                      f'Received: {device} {type(device)}'
                                      )

        value = protocol_read_func(obj=obj,
                                   device=device,
                                   prop=prop
                                   )
        return value

    def write(
            self,
            value: int or float or str,
            obj: BACnetObj or ModbusObj,
            device: BACnetDevice or ModbusDevice,
            priority: int = 11,  # TODO!! SURE?
            prop: ObjProperty = ObjProperty.presentValue
    ) -> None:
        if isinstance(device, BACnetDevice):
            protocol_write_func = self.write_bacnet
        elif isinstance(device, ModbusDevice):
            protocol_write_func = self.write_modbus
        else:
            raise NotImplementedError('Only BACnet, Modbus implemented. '
                                      f'Received: {device} {type(device)}'
                                      )
        protocol_write_func(value=value,
                            prop=prop,
                            priority=priority,
                            obj=obj,
                            device=device
                            )

    def write_with_check(
            self,
            value: int or float or str,
            obj: BACnetObj or ModbusObj,
            device: BACnetDevice or ModbusDevice,
            priority: int = 11,  # TODO!! SURE?
            prop: ObjProperty = ObjProperty.presentValue
    ) -> bool:
        if isinstance(device, BACnetDevice):
            protocol_write_with_check = self.write_with_check_bacnet
        elif isinstance(device, ModbusDevice):
            protocol_write_with_check = self.write_with_check_modbus
        else:
            raise NotImplementedError('Only BACnet, Modbus implemented. '
                                      f'Received: {device} {type(device)}'
                                      )
        _values_equal = protocol_write_with_check(value=value,
                                                  prop=prop,
                                                  priority=priority,
                                                  obj=obj,
                                                  device=device,
                                                  )
        return _values_equal
