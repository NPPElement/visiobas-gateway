import pytest
from gateway.models import ObjProperty


class TestObjProperty:
    @pytest.mark.parametrize(
        "id_",
        [i for i in range(387)],
    )
    def test_type_id_happy(self, id_):
        assert ObjProperty(id_).prop_id == id_

    @pytest.mark.parametrize(
        "id_",
        [-1, None, "bad_property", 2.5],
    )
    def test_bad_property(self, id_):
        with pytest.raises(ValueError):
            ObjProperty(id_)
