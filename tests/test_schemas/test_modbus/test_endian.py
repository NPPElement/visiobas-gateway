import pytest
from visiobas_gateway.schemas.modbus.endian import Endian, validate_endian


class TestEndian:
    @pytest.mark.parametrize(
        "value, value_str",
        [
            (">", "big"),
            ("<", "LITTle"),
            ("@", "AUTO"),
        ],
    )
    def test_construct_happy(self, value, value_str):
        assert Endian(value).value == value
        assert validate_endian(value_str) == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, ""],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            Endian(value)
