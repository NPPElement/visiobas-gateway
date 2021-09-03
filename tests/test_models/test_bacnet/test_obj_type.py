import pytest
from gateway.models import ObjType, ObjProperty


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
            (ObjType.ANALOG_INPUT, True),
            (ObjType.BINARY_OUTPUT, False),
            (ObjType.MULTI_STATE_INPUT, True),
            (ObjType.DEVICE, False),
        ],
    )
    def test_is_input(self, obj_type, expected):
        assert obj_type.is_input == expected

    @pytest.mark.parametrize(
        "obj_type, expected",
        [
            (ObjType.ANALOG_INPUT, False),
            (ObjType.BINARY_OUTPUT, True),
            (ObjType.MULTI_STATE_INPUT, False),
            (ObjType.DEVICE, False),
        ],
    )
    def test_is_output(self, obj_type, expected):
        assert obj_type.is_output == expected

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

    @pytest.mark.parametrize(
        "id_",
        [-1, None, "bad_type", 2.5],
    )
    def test_bad_type(self, id_):
        with pytest.raises(ValueError):
            ObjType(id_)

    @pytest.mark.parametrize(
        "obj_type, properties",
        [
            (ObjType.ANALOG_INPUT, (ObjProperty.presentValue, ObjProperty.statusFlags)),
            (
                ObjType.BINARY_OUTPUT,
                (
                    ObjProperty.presentValue,
                    ObjProperty.statusFlags,
                    ObjProperty.priorityArray,
                ),
            ),
        ],
    )
    def test_properties_happy(self, obj_type, properties):
        assert obj_type.properties == properties

    @pytest.mark.parametrize(
        "obj_type",
        [ObjType.DEVICE, ObjType.ACCUMULATOR],
    )
    def test_properties_not_defined(self, obj_type):
        with pytest.raises(NotImplementedError):
            obj_type.properties
