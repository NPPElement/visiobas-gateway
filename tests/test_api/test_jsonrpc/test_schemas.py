from visiobas_gateway.schemas.bacnet.obj_type import ObjType
from visiobas_gateway.schemas.bacnet.obj_property import ObjProperty
from visiobas_gateway.schemas.bacnet.priority import Priority
import pytest


class TestJsonRPCSetPointParams:
    @pytest.mark.parametrize(
        "data, expected_value",
        [
            ({"value": 2}, 2),
            ({"value": "2"}, 2),
            ({"value": "2.0"}, 2),
            ({"value": "22.22"}, 22.22),
        ],
    )
    def test_construct_happy(self, json_rpc_set_point_params_factory, data, expected_value):
        params = json_rpc_set_point_params_factory(**data)

        assert params.device_id == 846
        assert params.object_type == ObjType.ANALOG_OUTPUT
        assert params.object_id == 75
        assert params.priority == Priority.MANUAL_OPERATOR
        assert params.property == ObjProperty.PRESENT_VALUE

        assert params.value == expected_value
