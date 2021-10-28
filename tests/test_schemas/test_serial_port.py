import pytest
from pydantic import ValidationError


class TestSerialPort:
    @pytest.mark.parametrize(
        "serial_port",
        [
            "/dev/ttyS0",
            "/dev/ttyS2",
            "/dev/ttyUSB1",
        ],
    )
    def test_construct_happy(self, device_rtu_properties_factory, serial_port):
        rtu_properties = device_rtu_properties_factory(port=serial_port)
        assert rtu_properties.port == serial_port

    @pytest.mark.parametrize(
        "serial_port",
        [
            "bad_serial_port",
            "COM1",
            "/dev/ttyS666",
            "/dev/ttyUSB99",
            "/dev/ttyUSB",
            r"\dev\ttyS1",
        ],
    )
    def test_serial_port_construct_bad(self, device_rtu_properties_factory, serial_port):
        with pytest.raises(ValidationError):
            device_rtu_properties_factory(port=serial_port)
