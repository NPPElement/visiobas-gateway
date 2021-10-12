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
        bacnet_decoder = BACnetCoderMixin()
        assert (
            bacnet_decoder._decode_priority_array(priority_array=priority_array) == expected
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
        bacnet_decoder = BACnetCoderMixin()
        assert bacnet_decoder._encode_binary_present_value(value=value) == expected
