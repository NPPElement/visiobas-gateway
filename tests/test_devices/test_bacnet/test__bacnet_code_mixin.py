import pytest

from bacpypes.basetypes import PriorityArray, PriorityValue
from bacpypes.primitivedata import Null

from visiobas_gateway.devices.bacnet._bacnet_coder_mixin import BACnetCoderMixin


class TestBACnetCoderMixin:
    @pytest.mark.parametrize(
        "priority_array, expected",
        [
            (PriorityArray([PriorityValue(null=Null())] * 16), [None] * 16),
            (
                PriorityArray(
                    [
                        *[PriorityValue(null=Null())] * 7,
                        PriorityValue(real=3.3),
                        *[PriorityValue(null=Null())] * 8,
                    ]
                ),
                [*[None] * 7, 3.3, *[None] * 8],
            ),
        ],
    )
    def test__decode_priority_array(self, priority_array, expected):
        bacnet_coder = BACnetCoderMixin()
        assert (
            bacnet_coder._decode_priority_array(priority_array=priority_array) == expected
        )

    @pytest.mark.parametrize(
        "value, expected",
        [
            (1, "active"),
            (0, "inactive"),
            (1.0, "active"),
            (True, "active"),
            (False, "inactive"),
            (None, "inactive"),
            ("1", "active"),
            ("0", "active"),
        ],
    )
    def test__encode_binary_present_value(self, value, expected):
        bacnet_coder = BACnetCoderMixin()
        assert bacnet_coder._encode_binary_present_value(value=value) == expected

    @pytest.mark.parametrize(
        "obj_kwargs, expected_dict",
        [
            (
                {"79": "binary-input", "75": 3},
                {"binaryInput:3": ["presentValue", "statusFlags"]},
            ),
            (
                {"79": "binary-output", "75": 4},
                {"binaryOutput:4": ["presentValue", "statusFlags", "priorityArray"]},
            ),
        ],
    )
    def test__get_object_rpm_dict(self, bacnet_obj_factory, obj_kwargs, expected_dict):
        bacnet_coder = BACnetCoderMixin()
        obj = bacnet_obj_factory(**obj_kwargs)
        rpm_dict = bacnet_coder._get_object_rpm_dict(obj=obj)
        assert rpm_dict == expected_dict

    @pytest.mark.parametrize(
        "objs_kwargs, expected_dict",
        [
            (
                [{"79": "binary-input", "75": 3}, {"79": "binaryOutput", "75": 4}],
                {
                    "binaryInput:3": ["presentValue", "statusFlags"],
                    "binaryOutput:4": ["presentValue", "statusFlags", "priorityArray"],
                },
            ),
            (
                [{"79": "binary-input", "75": 6}, {"79": "analogInput", "75": 8}],
                {
                    "binaryInput:6": ["presentValue", "statusFlags"],
                    "analogInput:8": ["presentValue", "statusFlags"],
                },
            ),
        ],
    )
    def test__get_objects_rpm_dict(self, bacnet_obj_factory, objs_kwargs, expected_dict):
        bacnet_coder = BACnetCoderMixin()
        objs = [bacnet_obj_factory(**obj_kwargs) for obj_kwargs in objs_kwargs]
        rpm_dict = bacnet_coder._get_objects_rpm_dict(objs=objs)
        assert rpm_dict == expected_dict
