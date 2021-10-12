import pytest
from visiobas_gateway.schemas.modbus.func_code import ModbusReadFunc, ModbusWriteFunc


class TestModbusReadFunc:
    @pytest.mark.parametrize(
        "value",
        ["0x01", "0x02", "0x03", "0x04"],
    )
    def test_construct_happy(self, value):
        assert ModbusReadFunc(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, "0x06"],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            ModbusReadFunc(value)


class TestModbusWriteFunc:
    @pytest.mark.parametrize(
        "value",
        ["0x05", "0x06", "0x15", "0x16"],
    )
    def test_construct_happy(self, value):
        assert ModbusWriteFunc(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, "0x02"],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            ModbusWriteFunc(value)
