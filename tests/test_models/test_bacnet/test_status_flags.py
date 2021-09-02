import pytest
import pydantic
from gateway.models.bacnet.status_flags import StatusFlags, StatusFlag


class TestStatusFlag:
    @pytest.mark.parametrize(
        "flag",
        [1, 2, 4, 8],
    )
    def test_status_flag_happy(self, flag):
        assert StatusFlag(flag) == flag

    @pytest.mark.parametrize(
        "bad_flag",
        [-1, None, "bad_flag", 9, 3.3],
    )
    def test_status_flag_invalid(self, bad_flag):
        with pytest.raises(ValueError):
            StatusFlag(bad_flag)


class TestStatusFlags:
    @pytest.mark.parametrize(
        "before, after",
        [
            *[(i, flags) for i, flags in enumerate(range(16))],
            ("5", 5),  # duck typing
            (3.1, 3),  # duck typing
            (3.5, 3),  # duck typing
            (3.9, 3),  # duck typing
        ],
    )
    def test_status_flags_happy(self, before, after):
        assert StatusFlags(flags=before).flags == after

    @pytest.mark.parametrize(
        "flags",
        [-1, None, "bad", [1, 1, 1, 1]],
    )
    def test_status_flags_invalid_flags(self, flags):
        with pytest.raises(pydantic.ValidationError):
            StatusFlags(flags=flags)

    @pytest.mark.parametrize(
        "enable_flag, after",
        [
            (StatusFlag.OUT_OF_SERVICE, 7),
            (StatusFlag.OVERRIDEN, 11),
            (StatusFlag.FAULT, 13),
            (StatusFlag.IN_ALARM, 14),
        ],
    )
    def test_disable_happy(self, enable_flag, after):
        assert StatusFlags(flags=0b1111).disable(flag=enable_flag).flags == after

    @pytest.mark.parametrize(
        "enable_flag, after",
        [
            (StatusFlag.OUT_OF_SERVICE, 8),
            (StatusFlag.OVERRIDEN, 4),
            (StatusFlag.FAULT, 2),
            (StatusFlag.IN_ALARM, 1),
        ],
    )
    def test_enable_happy(self, enable_flag, after):
        assert StatusFlags(flags=0b0000).enable(flag=enable_flag).flags == after

    @pytest.mark.parametrize(
        "flag_check, expected",
        [
            (StatusFlag.OUT_OF_SERVICE, True),
            (StatusFlag.OVERRIDEN, False),
            (StatusFlag.FAULT, True),
            (StatusFlag.IN_ALARM, False),
        ],
    )
    def test_check(self, flag_check, expected):
        assert StatusFlags(flags=0b1010).check(flag=flag_check) == expected

    def test_for_http(self):
        """fixme"""
