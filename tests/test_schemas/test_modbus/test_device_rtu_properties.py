import pytest
from pydantic import ValidationError

from visiobas_gateway.schemas.serial_port import SerialPort
from visiobas_gateway.schemas.modbus.baudrate import BaudRate
from visiobas_gateway.schemas.modbus.parity import Parity
from visiobas_gateway.schemas.modbus.stopbits import StopBits
from visiobas_gateway.schemas.modbus.bytesize import Bytesize
from visiobas_gateway.schemas.modbus.device_rtu_properties import DeviceRtuProperties


class TestBaseDeviceModbusProperties:
    @pytest.mark.parametrize(
        "data, expected_unit",
        [
            ({"unit": 0}, 0),
            ({"unit": 1}, 1),
            ({"unit": "4"}, 4),
            ({"unit": 255}, 255),
        ],
    )
    def test_construct_happy(self, base_device_modbus_properties, data, expected_unit):
        base_device_modbus_properties = base_device_modbus_properties(**data)
        assert base_device_modbus_properties.unit == expected_unit

    @pytest.mark.parametrize(
        "data",
        [
            {"unit": "bad_unit"},
            {"unit": -1},
            {"unit": 333},
            {"unit": None},
        ],
    )
    def test_unit_bad(self, base_device_modbus_properties, data):
        with pytest.raises(ValidationError):
            base_device_modbus_properties(**data)


class TestDeviceRtuProperties:
    @pytest.mark.parametrize(
        "data, expected_port, expected_baudrate, expected_stopbits, "
        "expected_bytesize, expected_parity",
        [
            (
                {
                    "port": "/dev/ttyS1",
                    "baudrate": 9600,
                    "stopbits": 2,
                    "bytesize": 8,
                    "parity": "E",
                },
                SerialPort("/dev/ttyS1"),
                BaudRate._9600,
                StopBits._2,
                Bytesize._8,
                Parity.EVEN,
            ),
            (
                {
                    "port": "/dev/ttyUSB0",
                    "baudrate": 19_200,
                    "stopbits": 1,
                    "bytesize": 6,
                    "parity": "N",
                },
                SerialPort("/dev/ttyUSB0"),
                BaudRate._19200,
                StopBits._1,
                Bytesize._6,
                Parity.NONE,
            ),
        ],
    )
    def test_construct_happy(
        self,
        device_rtu_properties_factory,
        data,
        expected_port,
        expected_baudrate,
        expected_stopbits,
        expected_bytesize,
        expected_parity,
    ):
        rtu_properties = device_rtu_properties_factory(**data)
        assert isinstance(rtu_properties, DeviceRtuProperties)

        assert rtu_properties.port == expected_port
        assert rtu_properties.baudrate == expected_baudrate
        assert rtu_properties.stopbits == expected_stopbits
        assert rtu_properties.bytesize == expected_bytesize
        assert rtu_properties.parity == expected_parity
