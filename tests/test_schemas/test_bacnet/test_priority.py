import pytest
from visiobas_gateway.schemas.bacnet.priority import Priority


class TestPriority:
    @pytest.mark.parametrize(
        "value",
        [i for i in range(1, 17)],
    )
    def test_construct_happy(self, value):
        assert Priority(value).value == value

    @pytest.mark.parametrize(
        "value",
        ["bad_value", 17, 0, -1, None, ""],
    )
    def test_bad_value(self, value):
        with pytest.raises(ValueError):
            Priority(value)
