import pytest
from visiobas_gateway.schemas.modbus.baudrate import BaudRate


class TestBaudrate:
    @pytest.mark.parametrize(
        "value",
        [2_400, 4_800, 9_600, 19_200, 38_400, 57_600, 115_200],
    )
    def test_construct_happy(self, value):
        assert BaudRate(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, ""],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            BaudRate(value)
