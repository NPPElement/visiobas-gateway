import pytest
from visiobas_gateway.schemas.modbus.data_type import ModbusDataType


class TestModbusDataType:
    @pytest.mark.parametrize(
        "value",
        ["bits", "bool", "int", "uint", "float"],
    )
    def test_construct_happy(self, value):
        assert ModbusDataType(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, ""],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            ModbusDataType(value)
