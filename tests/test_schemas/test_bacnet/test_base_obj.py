import json

import pydantic
import pytest
from visiobas_gateway.schemas.bacnet.obj_type import ObjType


class TestBaseBACnetObj:
    def test_construct_happy(self, base_bacnet_obj_factory):
        obj1 = base_bacnet_obj_factory()
        assert obj1.id == 75
        assert obj1.name == "Name:Name/Name.Name"
        assert obj1.type == ObjType.ANALOG_INPUT
        assert obj1.property_list == {
            "template": "",
            "alias": "",
            "replace": {},
        }
        assert obj1.device_id == 846

        obj2 = base_bacnet_obj_factory(**{"79": 1})
        assert obj2.id == 75
        assert obj2.name == "Name:Name/Name.Name"
        assert obj2.type == ObjType.ANALOG_OUTPUT
        assert obj2.property_list == {
            "template": "",
            "alias": "",
            "replace": {},
        }
        assert obj2.device_id == 846

    @pytest.mark.parametrize(
        "data",
        [
            {"79": None},
            {"79": "bad_type"},
            {"79": 666},
            {"79": -1},
        ],
    )
    def test_construct_bad_type(self, base_bacnet_obj_factory, data):
        with pytest.raises(pydantic.ValidationError):
            base_bacnet_obj_factory(**data)

    def test_mqtt_topic(self, base_bacnet_obj_factory):
        obj = base_bacnet_obj_factory()
        assert obj.mqtt_topic == "Name/Name/Name/Name"

    @pytest.mark.parametrize(
        "data",
        [
            {"77": "other_name"},
            {"371": json.dumps({"other": "property_list"})},
        ],
    )
    def test___hash___same(self, base_bacnet_obj_factory, data):
        obj1 = base_bacnet_obj_factory(**data)
        obj2 = base_bacnet_obj_factory()
        assert hash(obj1) == hash(obj2)

    @pytest.mark.parametrize(
        "data",
        [
            {"75": 13},
            {"79": "binary-input"},
            {"846": 13},
        ],
    )
    def test___hash___different(self, base_bacnet_obj_factory, data):
        obj1 = base_bacnet_obj_factory(**data)
        obj2 = base_bacnet_obj_factory(
            **{
                "75": 12,
                "79": "analog-output",
                "846": 12,
            }
        )
        assert hash(obj1) != hash(obj2)
