import pytest
from visiobas_gateway.schemas.modbus.stopbits import StopBits


class TestModbusReadFunc:
    @pytest.mark.parametrize(
        "value",
        [1, 2],
    )
    def test_construct_happy(self, value):
        assert StopBits(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, "1"],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            StopBits(value)
