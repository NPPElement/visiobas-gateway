import asyncio
from gateway.verifier import BACnetVerifier
from gateway.models.bacnet.obj_property import ObjProperty

import pytest


class TestBACnetVerifier:
    def test_process_exception_happy(self, bacnet_obj_factory):
        try:
            from BAC0.core.io.IOExceptions import UnknownObjectError  # type: ignore
        except ImportError as import_exc:
            raise NotImplementedError from import_exc

        verifier = BACnetVerifier(override_threshold=8)
        bacnet_obj = bacnet_obj_factory(**{"85": asyncio.TimeoutError()})

        bacnet_obj = verifier.process_exception(
            obj=bacnet_obj, exc=bacnet_obj.present_value
        )
        assert bacnet_obj.present_value == "null"
        assert bacnet_obj.status_flags.flags == 0b0010
        assert bacnet_obj.reliability == "timeout"
        assert bacnet_obj.unreachable_in_row == 1
        assert bacnet_obj.existing is True

        bacnet_obj.set_property(value=UnknownObjectError(), prop=ObjProperty.presentValue)
        bacnet_obj = verifier.process_exception(
            obj=bacnet_obj, exc=bacnet_obj.present_value
        )
        assert bacnet_obj.present_value == "null"
        assert bacnet_obj.status_flags.flags == 0b0010
        assert bacnet_obj.reliability == "non-existent-object"
        assert bacnet_obj.unreachable_in_row == 2
        assert bacnet_obj.existing is False

        bacnet_obj.set_property(value=TypeError(), prop=ObjProperty.presentValue)
        bacnet_obj = verifier.process_exception(
            obj=bacnet_obj, exc=bacnet_obj.present_value
        )
        assert bacnet_obj.present_value == "null"
        assert bacnet_obj.status_flags.flags == 0b0010
        assert bacnet_obj.reliability == "decode-error"
        assert bacnet_obj.unreachable_in_row == 3

        bacnet_obj.set_property(value=AttributeError(), prop=ObjProperty.presentValue)
        bacnet_obj = verifier.process_exception(
            obj=bacnet_obj, exc=bacnet_obj.present_value
        )
        assert bacnet_obj.present_value == "null"
        assert bacnet_obj.status_flags.flags == 0b0010
        assert bacnet_obj.reliability == "AttributeError"
        assert bacnet_obj.unreachable_in_row == 4

    def test_process_exception_bad_exception(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=8)
        bacnet_obj = bacnet_obj_factory(**{"85": "not_exception"})
        with pytest.raises(ValueError):
            verifier.process_exception(obj=bacnet_obj, exc=bacnet_obj.present_value)

    def test_verify_status_flags_zero(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=8)
        bacnet_obj = bacnet_obj_factory(
            **{"103": "reliability", "verified_present_value": 85.8585}
        )

        bacnet_obj = verifier.verify_status_flags(
            obj=bacnet_obj, status_flags=bacnet_obj.status_flags
        )
        assert bacnet_obj.status_flags.flags == 0b0000
        assert bacnet_obj.reliability == ""

    def test_verify_status_flags_not_zero(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=8)
        bacnet_obj = bacnet_obj_factory(
            **{
                "103": "reliability",
                "111": [True, False, False, False],
                "verified_present_value": 85.8585,
            }
        )

        bacnet_obj = verifier.verify_status_flags(
            obj=bacnet_obj, status_flags=bacnet_obj.status_flags
        )
        assert bacnet_obj.status_flags.flags == 0b1000
        assert bacnet_obj.reliability == "reliability"

    def test_verify_status_flags_null_verified_pv(self, bacnet_obj_factory):
        verifier = BACnetVerifier(override_threshold=8)
        bacnet_obj = bacnet_obj_factory(
            **{
                "103": "reliability",
                "111": [True, False, False, False],
                "verified_present_value": "null",
            }
        )

        bacnet_obj = verifier.verify_status_flags(
            obj=bacnet_obj, status_flags=bacnet_obj.status_flags
        )
        assert bacnet_obj.status_flags.flags == 0b1010
        assert bacnet_obj.reliability == "reliability"

    @pytest.mark.parametrize(
        "present_value, verified_present_value",
        [
            (True, 1),
            ("active", 1),
            (False, 0),
            ("inactive", 0),
            ("null", "null"),
            ("   ", "null"),
            (None, "null"),
            (3.3333, 3.3),
            (3.0, 3),
            ("value", "value"),
        ],
    )
    def test_verify_present_value_affect_only_verified_present_value(
            self, bacnet_obj_factory, present_value, verified_present_value
    ):
        verifier = BACnetVerifier(override_threshold=8)

        bacnet_obj = bacnet_obj_factory(**{"85": present_value})
        bacnet_obj = verifier.verify_present_value(
            obj=bacnet_obj, value=bacnet_obj.present_value
        )
        assert bacnet_obj.verified_present_value == verified_present_value

    @pytest.mark.parametrize(
        "present_value, verified_present_value, reliability",
        [
            (float("inf"), "null", 2),
            (float("-inf"), "null", 3),
            (["bad_value_type"], "null", "invalid-value-type"),
        ],
    )
    def test_verify_present_value_also_affect_reliability(
            self, bacnet_obj_factory, present_value, verified_present_value, reliability
    ):
        verifier = BACnetVerifier(override_threshold=8)

        bacnet_obj = bacnet_obj_factory(**{"85": present_value})
        bacnet_obj = verifier.verify_present_value(
            obj=bacnet_obj, value=bacnet_obj.present_value
        )
        assert bacnet_obj.verified_present_value == verified_present_value
        assert bacnet_obj.reliability == reliability

    @pytest.mark.parametrize(
        "priority_array, status_flags",
        [
            (
                    [
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        3.3,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                    ],
                    0b0100,
            ),
            ([None] * 16, 0b0000),
        ],
    )
    def test_verify_priority_array_happy(
            self, bacnet_obj_factory, priority_array, status_flags
    ):
        verifier = BACnetVerifier(override_threshold=8)

        bacnet_obj = bacnet_obj_factory(**{"87": priority_array})

        bacnet_obj = verifier.verify_priority_array(
            obj=bacnet_obj, priority_array=bacnet_obj.priority_array
        )
        assert bacnet_obj.status_flags.flags == status_flags


    def test_verify(self):