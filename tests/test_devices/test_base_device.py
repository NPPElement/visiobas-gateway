from visiobas_gateway.schemas.protocol import Protocol


class TestBaseDevice:
    async def test_construct(self, base_device_factory):
        base_device = base_device_factory()
        assert base_device.id == 75
        assert base_device.protocol == Protocol.MODBUS_RTU
