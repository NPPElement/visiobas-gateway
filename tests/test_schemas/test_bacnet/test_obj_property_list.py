import pytest
from pydantic import ValidationError

from visiobas_gateway.schemas.bacnet.obj_property_list import BaseBACnetObjPropertyList


class TestBaseObjPropertyList:
    @pytest.mark.parametrize(
        "data, expected_poll_period",
        [
            ({"pollPeriod": 30}, 30),
            ({"pollPeriod": 45.5}, 45.5),
        ],
    )
    def test_construct_happy(
        self,
        base_obj_property_list_factory,
        data,
        expected_poll_period,
    ):
        base_obj_property_list = base_obj_property_list_factory(**data)

        assert isinstance(base_obj_property_list, BaseBACnetObjPropertyList)
        assert base_obj_property_list.poll_period == expected_poll_period

    @pytest.mark.parametrize(
        "data",
        [
            {"pollPeriod": -1},
            {"pollPeriod": "bad_poll_period"},
            {"pollPeriod": ""},
            {"pollPeriod": None},
        ],
    )
    def test_bad_poll_period(
        self,
        base_obj_property_list_factory,
        data,
    ):
        with pytest.raises(ValidationError):
            base_obj_property_list_factory(**data)
