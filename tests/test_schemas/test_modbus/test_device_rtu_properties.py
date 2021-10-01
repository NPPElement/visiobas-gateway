class TestDeviceRtuProperties:
    def test_construct_happy(self, device_rtu_properties_factory):
        rtu_properties = device_rtu_properties_factory()
        assert rtu_properties.port == "/dev/ttyS0"
        assert rtu_properties.unit == 10
        assert rtu_properties.baudrate == 9600
        assert rtu_properties.stopbits == 1
        assert rtu_properties.bytesize == 8
        assert rtu_properties.parity == "N"
