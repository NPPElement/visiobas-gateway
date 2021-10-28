from visiobas_gateway.schemas.protocol import Protocol
from visiobas_gateway.devices.base_device import BaseDevice
import logging
from visiobas_gateway.gateway import Gateway
from visiobas_gateway.schemas.bacnet.device_obj import DeviceObj


class TestBaseDevice:
    async def test_construct(self, base_device_factory):
        base_device = base_device_factory()

        assert isinstance(base_device, BaseDevice)
        assert isinstance(base_device._gtw, Gateway)
        assert isinstance(base_device._device_obj, DeviceObj)

        assert base_device.id == 75
        assert base_device.protocol == Protocol.MODBUS_RTU
        assert isinstance(base_device._LOG, logging.Logger)
