from visiobas_gateway.schemas.bacnet.obj_type import ObjType
from visiobas_gateway.schemas.bacnet.obj_property import ObjProperty
from visiobas_gateway.schemas.bacnet.priority import Priority


class TestJsonRPCSetPointParams:
    def test_construct_happy(self, json_rpc_set_point_params_factory):
        params = json_rpc_set_point_params_factory()
        assert params.device_id == 846
        assert params.object_type == ObjType.ANALOG_OUTPUT
        assert params.object_id == 75
        assert params.priority == Priority.MANUAL_OPERATOR
        assert params.value == 22.22
        assert params.property == ObjProperty.PRESENT_VALUE
