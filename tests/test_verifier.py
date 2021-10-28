import asyncio
import datetime

from visiobas_gateway.schemas.bacnet.obj_type import ObjType
from visiobas_gateway.verifier import BACnetVerifier
from visiobas_gateway.schemas.bacnet.obj_property import ObjProperty
from visiobas_gateway.schemas.bacnet.reliability import Reliability
from visiobas_gateway.schemas.bacnet.priority import Priority

import pytest


class TestBACnetVerifier:
    def test_process_exception_happy(self, bacnet_obj_factory):
        try:
            from BAC0.core.io.IOExceptions import UnknownObjectError  # type: ignore
        except ImportError as import_exc:
            raise NotImplementedError from import_exc

        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory(**{"85": asyncio.TimeoutError()})

        verified_obj = verifier.process_exception(
            obj=bacnet_obj, exc=bacnet_obj.present_value
        )
        assert verified_obj.present_value == "null"
        assert verified_obj.status_flags.flags == 0b0010
        assert verified_obj.reliability == "timeout"
        assert verified_obj.unreachable_in_row == 1
        assert verified_obj.existing is True

        verified_obj.set_property(
            value=UnknownObjectError(), prop=ObjProperty.PRESENT_VALUE
        )
        verified_obj_2 = verifier.process_exception(
            obj=verified_obj, exc=verified_obj.present_value
        )
        assert verified_obj_2.present_value == "null"
        assert verified_obj_2.status_flags.flags == 0b0010
        assert verified_obj_2.reliability == Reliability.NO_SENSOR
        assert verified_obj_2.unreachable_in_row == 2
        assert verified_obj_2.existing is False

        verified_obj_2.set_property(value=TypeError(), prop=ObjProperty.PRESENT_VALUE)
        verified_obj_3 = verifier.process_exception(
            obj=verified_obj_2, exc=verified_obj_2.present_value
        )
        assert verified_obj_3.present_value == "null"
        assert verified_obj_3.status_flags.flags == 0b0010
        assert verified_obj_3.reliability == "decode-error"
        assert verified_obj_3.unreachable_in_row == 3

        verified_obj_3.set_property(value=AttributeError(), prop=ObjProperty.PRESENT_VALUE)
        verified_obj_4 = verifier.process_exception(
            obj=verified_obj_3, exc=verified_obj_3.present_value
        )
        assert verified_obj_4.present_value == "null"
        assert verified_obj_4.status_flags.flags == 0b0010
        assert verified_obj_4.reliability == "AttributeError"
        assert verified_obj_4.unreachable_in_row == 4

        assert (
            id(bacnet_obj)
            == id(verified_obj)
            == id(verified_obj_2)
            == id(verified_obj_3)
            == id(verified_obj_4)
        )

    def test_process_exception_bad_exception(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory(**{"85": "not_exception"})
        with pytest.raises(ValueError):
            verifier.process_exception(obj=bacnet_obj, exc=bacnet_obj.present_value)

    def test_verify_status_flags_zero(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory(
            **{"103": "reliability", "verified_present_value": 85.8585}
        )
        verified_obj = verifier.verify_status_flags(
            obj=bacnet_obj, status_flags=bacnet_obj.status_flags
        )
        assert id(verified_obj) == id(bacnet_obj)
        assert verified_obj.status_flags.flags == 0b0000
        assert verified_obj.reliability == Reliability.NO_FAULT_DETECTED

    def test_verify_status_flags_not_zero(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory(
            **{
                "103": "reliability",
                "111": [True, False, False, False],
                "verified_present_value": 85.8585,
            }
        )
        verified_obj = verifier.verify_status_flags(
            obj=bacnet_obj, status_flags=bacnet_obj.status_flags
        )
        assert id(verified_obj) == id(bacnet_obj)
        assert verified_obj.status_flags.flags == 0b1000
        assert verified_obj.reliability == "reliability"

    def test_verify_status_flags_null_verified_pv(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory(
            **{
                "103": "reliability",
                "111": [True, False, False, False],
                "verified_present_value": "null",
            }
        )
        verified_obj = verifier.verify_status_flags(
            obj=bacnet_obj, status_flags=bacnet_obj.status_flags
        )
        assert id(verified_obj) == id(bacnet_obj)
        assert verified_obj.status_flags.flags == 0b1010
        assert verified_obj.reliability == "reliability"

    @pytest.mark.parametrize(
        "present_value, verified_present_value",
        [
            (True, 1),
            ("active", 1),
            (False, 0),
            ("inactive", 0),
            (3.3333, 3.3),
            (3.0, 3),
            ("1234", 1234),
            ("12.001", 12),
        ],
    )
    def test_verify_present_value_happy(
        self, bacnet_obj_factory, present_value, verified_present_value
    ):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)

        bacnet_obj = bacnet_obj_factory(**{"85": present_value})
        verified_obj = verifier.verify_present_value(
            obj=bacnet_obj, value=bacnet_obj.present_value
        )
        assert id(verified_obj) == id(bacnet_obj)
        assert verified_obj.verified_present_value == verified_present_value
        assert verified_obj.reliability == Reliability.NO_FAULT_DETECTED

    @pytest.mark.parametrize(
        "present_value, verified_present_value, reliability",
        [
            (float("inf"), "null", Reliability.OVER_RANGE),
            (float("-inf"), "null", Reliability.UNDER_RANGE),
            (["bad_value_type"], "null", Reliability.NO_OUTPUT),
            ("null", "null", Reliability.NO_OUTPUT),
            (None, "null", Reliability.NO_OUTPUT),
            ("   ", "null", "unexpected-value"),
            ("bad_value", "null", "unexpected-value"),
            (..., "null", "unexpected-type"),
        ],
    )
    def test_verify_present_value_reliability_affected(
        self, bacnet_obj_factory, present_value, verified_present_value, reliability
    ):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)

        bacnet_obj = bacnet_obj_factory(**{"85": present_value})
        verified_obj = verifier.verify_present_value(
            obj=bacnet_obj, value=bacnet_obj.present_value
        )
        assert id(verified_obj) == id(bacnet_obj)
        assert verified_obj.verified_present_value == verified_present_value
        assert verified_obj.reliability == reliability

    @pytest.mark.parametrize(
        "priority_array, status_flags",
        [
            (
                [*[None] * 8, 3.3, *[None] * 7],
                0b0100,
            ),
            ([None] * 16, 0b0000),
        ],
    )
    def test_verify_priority_array_happy(
        self, bacnet_obj_factory, priority_array, status_flags
    ):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)

        bacnet_obj = bacnet_obj_factory(**{"87": priority_array})

        verified_obj = verifier.verify_priority_array(
            obj=bacnet_obj,
            priority_array=bacnet_obj.priority_array,
            override_threshold=verifier.override_threshold,
        )
        assert id(verified_obj) == id(bacnet_obj)
        assert verified_obj.status_flags.flags == status_flags

    def test_verify_exception(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory(**{"85": ValueError()})

        verified_obj = verifier.verify(obj=bacnet_obj)
        assert id(verified_obj) == id(bacnet_obj)
        assert verified_obj.status_flags.flags == 0b0010

    @pytest.mark.parametrize(
        "data, expected_reliability",
        [
            (
                {"79": ObjType.BINARY_INPUT},
                "bad_binary_value",
            ),
            (
                {"79": ObjType.BINARY_INPUT, "85": 1},
                Reliability.NO_FAULT_DETECTED,
            ),
            (
                {"79": ObjType.MULTI_STATE_OUTPUT},
                "bad_multistate_value",
            ),
            (
                {"79": ObjType.MULTI_STATE_OUTPUT, "85": 4},
                Reliability.NO_FAULT_DETECTED,
            ),
        ],
    )
    def test_type_check(self, bacnet_obj_factory, data, expected_reliability):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory(**data)
        assert bacnet_obj.reliability == Reliability.NO_FAULT_DETECTED

        verified_obj = verifier.type_check(obj=bacnet_obj)
        assert id(verified_obj) == id(bacnet_obj)
        assert verified_obj.reliability == expected_reliability

    def test_verify_happy(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory(
            **{
                "85": 66.666,
                "87": [None] * 16,
            }
        )
        assert bacnet_obj.changed is None
        verified_obj = verifier.verify(obj=bacnet_obj)
        assert verified_obj.present_value == 66.7
        assert isinstance(verified_obj.changed, datetime.datetime)
        assert str(verified_obj.changed) == "2011-11-11 11:11:11"

        verified_obj.set_property(value=33.333, prop=ObjProperty.PRESENT_VALUE)
        verified_obj_2 = verifier.verify(obj=verified_obj)
        assert str(verified_obj_2.updated) > "2011-11-11 22:22:22"

        verified_obj_3 = verifier.verify(obj=verified_obj_2)
        assert str(verified_obj_3.changed) > "2011-11-11 22:22:22"

        assert (
            id(bacnet_obj) == id(verified_obj) == id(verified_obj_2) == id(verified_obj_3)
        )

    def test_verify_objects(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=Priority.MANUAL_OPERATOR)
        bacnet_obj = bacnet_obj_factory()

        bacnet_obj.set_property(value=66.666, prop=ObjProperty.PRESENT_VALUE)
        bacnet_objects = [bacnet_obj] * 3

        bacnet_objects = verifier.verify_objects(objs=bacnet_objects)
        for obj in bacnet_objects:
            assert obj.present_value == 66.7
            assert str(obj.updated) > "2011-11-11 11:11:11"
            assert str(obj.changed) > "2011-11-11 11:11:11"
