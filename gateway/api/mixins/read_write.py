from typing import Any, Union, Optional

# from .bacnet_rw import BACnetRWMixin
from .modbus_rw import ModbusRWMixin
# from ...connectors import BACnetDevice, ModbusDevice
from ...models import ObjProperty, Protocol

# Aliases
DeviceAlias = Any  # Union['...devices.AsyncModbusDevice',]
ObjAlias = Any  # Union['...models.BACnetObj', '...models.ModbusObj',]


class ReadWriteMixin(ModbusRWMixin):  # todo BACnetRWMixin
    async def read(self, obj: ObjAlias, device: DeviceAlias,
                   prop: ObjProperty = ObjProperty.presentValue) -> Any:
        """
        Args:
            obj: Object instance.
            device: Device instance.
            prop: Property of object.

        Returns:
            Read property's value.
        """
        protocol = device.protocol

        if protocol in {Protocol.MODBUS_TCP,
                        Protocol.MODBUS_RTU,
                        Protocol.MODBUS_RTUOVERTCP, }:
            protocol_read_coro = self.read_modbus

        # elif protocol is Protocol.BACNET:
        # protocol_read_func = self.read_bacnet
        else:
            raise NotImplementedError('Only BACnet, Modbus implemented. '
                                      f'Received: {device} {type(device)}')
        value = await protocol_read_coro(obj=obj, device=device, prop=prop)
        return value

    async def write(self, value: Optional[Union[int, float, str]],
                    obj: ObjAlias, device: DeviceAlias,
                    priority: int = 11, prop: ObjProperty = ObjProperty.presentValue
                    ) -> None:
        """
        # TODO priority

        Args:
            value: Value to write in object.
            obj: Object instance.
            device: Device instance.
            priority: Priority of value.
            prop: Property of object to write.
        """
        protocol = device.protocol

        if protocol in {Protocol.MODBUS_TCP,
                        Protocol.MODBUS_RTU,
                        Protocol.MODBUS_RTUOVERTCP, }:
            protocol_write_coro = self.write_modbus
        # if protocol is Protocol.BACNET:
        #     protocol_write_func = self.write_bacnet
        else:
            raise NotImplementedError('Only BACnet, Modbus implemented. '
                                      f'Received: {device} {type(device)}')
        await protocol_write_coro(value=value, prop=prop, priority=priority,
                                  obj=obj, device=device)

    async def write_with_check(self, value: Optional[Union[int, float, str]],
                               obj: ObjAlias, device: DeviceAlias,
                               priority: int = 11,
                               prop: ObjProperty = ObjProperty.presentValue
                               ) -> bool:
        """
        # TODO: priority
        Args:
            value: Value to write in object.
            obj: Object instance.
            device: Device instance.
            priority: Priority of value.
            prop: Property of object to write.

        Returns:
            Is write value and read value are equal.
        """
        protocol = device.protocol

        if protocol in {Protocol.MODBUS_TCP,
                        Protocol.MODBUS_RTU,
                        Protocol.MODBUS_RTUOVERTCP, }:
            protocol_write_func = self.write_modbus
            protocol_read_func = self.read_modbus
        # if protocol is Protocol.BACNET:
        #     protocol_write_func = self.write_bacnet
        else:
            raise NotImplementedError('Only BACnet, Modbus implemented. '
                                      f'Received: {device} {type(device)}')
        await protocol_write_func(value=value, obj=obj, device=device,
                                  priority=priority, prop=prop)
        read_value = await protocol_read_func(obj=obj, device=device)

        return value == read_value
