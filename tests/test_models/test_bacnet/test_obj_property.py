import pytest
from gateway.models import ObjProperty


class TestObjProperty:
    @pytest.mark.parametrize(
        "id_",
        [i for i in range(387)],
    )
    def test_type_id(self, id_):
        assert ObjProperty(id_).prop_id == id_
