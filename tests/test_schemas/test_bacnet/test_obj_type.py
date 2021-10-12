import pytest
from visiobas_gateway.schemas.bacnet.obj_type import (
    ObjType,
)


class TestObjType:
    @pytest.mark.parametrize(
        "id_",
        [*{i for i in range(55)} - {31}],
    )
    def test_construct_happy(self, id_):
        assert ObjType(id_).value == id_

    @pytest.mark.parametrize(
        "id_",
        [-1, None, "bad_type", 2.5],
    )
    def test_bad_type(self, id_):
        with pytest.raises(ValueError):
            ObjType(id_)

# @pytest.mark.parametrize(
#     "obj_type, expected",
#     [
#         (ObjType.ANALOG_INPUT, True),
#         (ObjType.ANALOG_OUTPUT, True),
#         (ObjType.BINARY_INPUT, False),
#         (ObjType.MULTI_STATE_INPUT, False),
#         (ObjType.DEVICE, False),
#     ],
# )
# def test_is_analog(obj_type, expected):
#     assert obj_type in ANALOG_TYPES
#
#
# @pytest.mark.parametrize(
#     "obj_type, expected",
#     [
#         (ObjType.ANALOG_INPUT, False),
#         (ObjType.ANALOG_OUTPUT, False),
#         (ObjType.BINARY_INPUT, False),
#         (ObjType.MULTI_STATE_INPUT, False),
#         (ObjType.DEVICE, False),
#     ],
# )
# def test_is_binary(obj_type, expected):
#     assert obj_type in ANALOG_TYPES
#
#
# @pytest.mark.parametrize(
#         "obj_type, expected",
#         [
#             (ObjType.ANALOG_INPUT, True),
#             (ObjType.BINARY_OUTPUT, False),
#             (ObjType.MULTI_STATE_INPUT, True),
#             (ObjType.BINARY_INPUT, True),
#             (ObjType.DEVICE, False),
#         ],
# )
# def test_is_input(obj_type, expected):
#     assert obj_type in INPUT_TYPES

# @pytest.mark.parametrize(
#     "obj_type, expected",
#     [
#         (ObjType.ANALOG_INPUT, False),
#         (ObjType.BINARY_OUTPUT, True),
#         (ObjType.MULTI_STATE_INPUT, False),
#         (ObjType.DEVICE, False),
#     ],
# )
# def test_is_output(self, obj_type, expected):
#     assert obj_type.is_output == expected

# @pytest.mark.parametrize(
#     "obj_type, expected",
#     [
#         (ObjType.ANALOG_INPUT, False),
#         (ObjType.BINARY_INPUT, True),
#         (ObjType.MULTI_STATE_INPUT, True),
#         (ObjType.DEVICE, False),
#     ],
# )
# def test_is_discrete(self, obj_type, expected):
#     assert obj_type.is_discrete == expected

# @pytest.mark.parametrize(
#     "obj_type, properties",
#     [
#         (ObjType.ANALOG_INPUT, (ObjProperty.presentValue, ObjProperty.statusFlags)),
#         (
#             ObjType.BINARY_OUTPUT,
#             (
#                 ObjProperty.presentValue,
#                 ObjProperty.statusFlags,
#                 ObjProperty.priorityArray,
#             ),
#         ),
#     ],
# )
# def test_properties_happy(self, obj_type, properties):
#     assert obj_type.properties == properties

# fixme use in obj
# @pytest.mark.parametrize(
#     "obj_type",
#     [ObjType.DEVICE, ObjType.ACCUMULATOR],
# )
# def test_properties_not_defined(self, obj_type):
#     with pytest.raises(NotImplementedError):
#         obj_type.properties
