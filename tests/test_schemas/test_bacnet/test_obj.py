import asyncio

import pytest

from visiobas_gateway.schemas import ObjType
from visiobas_gateway.schemas.bacnet.obj_property import ObjProperty
from visiobas_gateway.schemas.bacnet.reliability import Reliability
from visiobas_gateway.schemas.bacnet.obj import DEFAULT_PRIORITY_ARRAY


class TestBACnetObj:
    def test_construct_happy(self, bacnet_obj_factory):
        bacnet_obj = bacnet_obj_factory()
        assert bacnet_obj.resolution == 0.1
        assert bacnet_obj.reliability == Reliability.NO_FAULT_DETECTED
        assert bacnet_obj.status_flags.flags == 0b0000
        assert bacnet_obj.present_value == 85.8585
        assert str(bacnet_obj.updated) == "2011-11-11 11:11:11"
        assert bacnet_obj.unreachable_in_row == 0

    def test_set_property_bad_property(self, bacnet_obj_factory):
        with pytest.raises(ValueError):
            bacnet_obj = bacnet_obj_factory()
            bacnet_obj.set_property(value="value", prop="bad_prop")

        with pytest.raises(ValueError):
            bacnet_obj = bacnet_obj_factory()
            # No property `derivativeConstant` in BACnetObj `pydantic` model.
            bacnet_obj.set_property(value="value", prop=ObjProperty.DERIVATIVE_CONSTANT)

    def test_set_property_happy(self, bacnet_obj_factory):
        bacnet_obj = bacnet_obj_factory()
        assert bacnet_obj.present_value == 85.8585
        assert str(bacnet_obj.updated) == "2011-11-11 11:11:11"

        bacnet_obj.set_property(value=58.5858, prop=ObjProperty.PRESENT_VALUE)
        assert bacnet_obj.present_value == 58.5858
        assert str(bacnet_obj.updated) > "2011-11-11 11:11:11"
        assert bacnet_obj.unreachable_in_row == 0

        bacnet_obj.set_property(value=2, prop=ObjProperty.STATUS_FLAGS)
        assert bacnet_obj.status_flags.flags == 2
        assert bacnet_obj.unreachable_in_row == 0

    @pytest.mark.parametrize(
        "priority_array, expected",
        [
            (None, ",,,,,,,,,,,,,,,"),
            ([None], ",,,,,,,,,,,,,,,"),
            (DEFAULT_PRIORITY_ARRAY, ",,,,,,,,,,,,,,,"),
            ([*[None] * 8, 40.5, *[None] * 5, 49.2, None], ",,,,,,,,40.5,,,,,,49.2,"),
        ],
    )
    def test_priority_array_to_http_str(self, bacnet_obj_factory, priority_array, expected):
        bacnet_obj = bacnet_obj_factory(**{"87": priority_array})
        assert (
            bacnet_obj.priority_array_to_http_str(priority_array=bacnet_obj.priority_array)
            == expected
        )

    @pytest.mark.parametrize(
        "data, expected, verified_expected",
        [
            (
                {"103": "", "111": 8, "85": 6.666, "79": 0},
                "75 0 6.666 0 0;",
                "75 0 6.7 0 0;",
            ),
            (
                {"103": Reliability.OVER_RANGE, "79": ObjType.BINARY_OUTPUT},
                "75 4 85.8585 ,,,,,,,,,,,,,,, 0 2;",
                "75 4 85.8585 ,,,,,,,,,,,,,,, 0 0;",  # only fault flag pass in http
            ),
            (
                {"103": Reliability.OVER_RANGE, "85": asyncio.TimeoutError()},
                "75 0  0 2;",  # unverified presentValue(85)
                "75 0 null 2 timeout;",  # only fault flag pass in http
            ),
        ],
    )
    def test_to_http_str(self, bacnet_obj_factory, data, expected, verified_expected):
        from visiobas_gateway.verifier import BACnetVerifier

        bacnet_obj = bacnet_obj_factory(**data)
        assert bacnet_obj.to_http_str(obj=bacnet_obj) == expected

        verified_bacnet_obj = BACnetVerifier().verify(obj=bacnet_obj)
        assert verified_bacnet_obj.to_http_str(obj=verified_bacnet_obj) == verified_expected
