from typing import Any, Union, Optional

from .bacnet_rw import BACnetRWMixin
from .modbus_rw import ModbusRWMixin
from ...models import ObjProperty, Protocol
from ...utils import get_file_logger

# Aliases
DeviceAlias = Any  # Union['...devices.AsyncModbusDevice',]
ObjAlias = Any  # Union['...models.BACnetObj', '...models.ModbusObj',]

_LOG = get_file_logger(name=__name__)


class ReadWriteMixin(ModbusRWMixin, BACnetRWMixin):
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

        elif protocol is Protocol.BACNET:
            protocol_read_coro = self.read_bacnet
        else:
            raise NotImplementedError('Only BACnet, Modbus implemented. '
                                      f'Received: {device} {type(device)}')
        value = await protocol_read_coro(obj=obj, device=device, prop=prop)
        return value

    async def write(self, value: Optional[Union[int, float]],
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
        elif protocol is Protocol.BACNET:
            protocol_write_coro = self.write_bacnet
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

        if protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTU,
                        Protocol.MODBUS_RTUOVERTCP, }:
            protocol_write_coro = self.write_modbus
            protocol_read_coro = self.read_modbus
        elif protocol is Protocol.BACNET:
            protocol_write_coro = self.write_bacnet
            protocol_read_coro = self.read_bacnet
        else:
            raise NotImplementedError('Only BACnet, Modbus implemented. '
                                      f'Received: {device} {type(device)}')
        await protocol_write_coro(value=value, obj=obj, device=device,
                                  priority=priority, prop=prop)
        read_value = await protocol_read_coro(obj=obj, device=device, prop=prop)
        is_consistent = value == read_value

        _LOG.debug('Write with check called',
                   extra={'device_id': obj.device_id, 'object_id': obj.id,
                          'object_type': obj.type, 'value_written': value,
                          'value_read': read_value,
                          'values_are_consistent': is_consistent, })
        return is_consistent
