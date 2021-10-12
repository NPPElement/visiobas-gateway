import pytest
from visiobas_gateway.schemas.bacnet.reliability import Reliability


class TestReliability:
    @pytest.mark.parametrize(
        "value",
        [*{i for i in range(16)} - {11}],
    )
    def test_construct_happy(self, value):
        assert Reliability(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, -1, None, ""],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            Reliability(value)
