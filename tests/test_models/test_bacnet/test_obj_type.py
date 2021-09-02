import pytest
from gateway.models import ObjType


class TestObjType:
    @pytest.mark.parametrize(
        "id_",
        [i for i in range(55)],
    )
    def test_type_id(self, id_):
        assert ObjType(id_).type_id == id_

    @pytest.mark.parametrize(
        "obj_type, expected",
        [
            (ObjType.ANALOG_INPUT, True),
            (ObjType.BINARY_INPUT, False),
            (ObjType.MULTI_STATE_INPUT, False),
            (ObjType.DEVICE, False),
        ],
    )
    def test_is_analog(self, obj_type, expected):
        assert obj_type.is_analog == expected

    @pytest.mark.parametrize(
        "obj_type, expected",
        [
            (ObjType.ANALOG_INPUT, False),
            (ObjType.BINARY_INPUT, True),
            (ObjType.MULTI_STATE_INPUT, True),
            (ObjType.DEVICE, False),
        ],
    )
    def test_is_discrete(self, obj_type, expected):
        assert obj_type.is_discrete == expected

    def test_properties(self):
        """fixme"""
