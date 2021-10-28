import pytest
from visiobas_gateway.schemas.modbus.bytesize import Bytesize


class TestBytesize:
    @pytest.mark.parametrize(
        "value",
        [i for i in range(5, 9)],
    )
    def test_construct_happy(self, value):
        assert Bytesize(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, ""],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            Bytesize(value)
