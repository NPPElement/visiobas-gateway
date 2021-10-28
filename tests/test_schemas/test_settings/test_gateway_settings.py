from visiobas_gateway.schemas.settings import GatewaySettings
from visiobas_gateway.schemas.bacnet.priority import Priority
import pytest
from pydantic import ValidationError


class TestGatewaySettings:
    @pytest.mark.parametrize(
        "data, expected_update_period, expected_unreachable_reset_period, "
        "expected_unreachable_threshold, expected_override_threshold, "
        "expected_poll_device_ids",
        [
            (
                {
                    "update_period": 4444,
                    "unreachable_reset_period": 999,
                    "unreachable_threshold": 2,
                    "override_threshold": 10,
                    "poll_device_ids": [11, 22],
                },
                4444,
                999,
                2,
                Priority.GCL_PLUS,
                [11, 22],
            ),
            (
                {"poll_device_ids": [12, 13]},
                3600,
                1800,
                3,
                Priority.MANUAL_OPERATOR,
                [12, 13],
            ),
        ],
    )
    def test_construct_happy(
        self,
        gateway_settings_factory,
        data,
        expected_update_period,
        expected_unreachable_reset_period,
        expected_unreachable_threshold,
        expected_override_threshold,
        expected_poll_device_ids,
    ):
        gateway_settings = gateway_settings_factory(**data)

        assert isinstance(gateway_settings, GatewaySettings)
        assert gateway_settings.update_period == expected_update_period
        assert (
            gateway_settings.unreachable_reset_period == expected_unreachable_reset_period
        )
        assert gateway_settings.unreachable_threshold == expected_unreachable_threshold
        assert gateway_settings.override_threshold == expected_override_threshold
        assert gateway_settings.poll_device_ids == expected_poll_device_ids

    @pytest.mark.parametrize(
        "data, expected_poll_device_ids",
        [
            ({"poll_device_ids": [22, 11, 22, 11, 33]}, [11, 22, 33]),
            ({"poll_device_ids": [13, 13]}, [13]),
        ],
    )
    def test_remove_duplicated_ids(
        self, gateway_settings_factory, data, expected_poll_device_ids
    ):
        gateway_settings = gateway_settings_factory(**data)

        assert isinstance(gateway_settings, GatewaySettings)
        assert gateway_settings.poll_device_ids == expected_poll_device_ids

    @pytest.mark.parametrize(
        "data",
        [
            {"update_period": "bad_update_period"},
            {"update_period": 0},
            {"update_period": -99},
            {"update_period": 1000},
        ],
    )
    def test_update_period_bad(self, gateway_settings_factory, data):
        with pytest.raises(ValidationError):
            gateway_settings_factory(**data)

    @pytest.mark.parametrize(
        "data",
        [
            {"unreachable_reset_period": "bad_unreachable_reset_period"},
            {"unreachable_reset_period": 0},
            {"unreachable_reset_period": -99},
            {"unreachable_reset_period": 99},
        ],
    )
    def test_unreachable_reset_period_bad(self, gateway_settings_factory, data):
        with pytest.raises(ValidationError):
            gateway_settings_factory(**data)

    @pytest.mark.parametrize(
        "data",
        [
            {"unreachable_threshold": "bad_unreachable_threshold"},
            {"unreachable_threshold": 0},
            {"unreachable_threshold": -1},
        ],
    )
    def test_unreachable_threshold_bad(self, gateway_settings_factory, data):
        with pytest.raises(ValidationError):
            gateway_settings_factory(**data)

    @pytest.mark.parametrize(
        "data",
        [
            {"poll_device_ids": "bad_poll_device_ids"},
            {"poll_device_ids": []},
            {"poll_device_ids": [0]},
            {"poll_device_ids": [-1]},
        ],
    )
    def test_poll_device_ids_bad(self, gateway_settings_factory, data):
        with pytest.raises(ValidationError):
            gateway_settings_factory(**data)
