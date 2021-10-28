import pytest
from visiobas_gateway.schemas.modbus.parity import Parity


class TestModbusReadFunc:
    @pytest.mark.parametrize(
        "value",
        ["N", "E", "O"],
    )
    def test_construct_happy(self, value):
        assert Parity(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, "О"],  # used russian `O` instead english `O`
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            Parity(value)
