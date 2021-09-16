import pytest
from visiobas_gateway.schemas import ObjProperty


class TestObjProperty:
    @pytest.mark.parametrize(
        "id_",
        [
            *{i for i in range(387)}
            - {
                18,
                51,
                55,
                95,
                101,
                129,
                138,
                194,
                198,
                199,
                200,
                201,
                216,
                217,
                223,
                224,
                225,
                236,
                237,
                238,
                239,
                240,
                241,
                242,
                243,
                284,
                293,
                299,
                312,
                313,
                314,
                315,
                316,
                324,
                325,
            }
            | {846}
        ],
    )
    def test_type_id_happy(self, id_):
        assert ObjProperty(id_).id == id_

    @pytest.mark.parametrize(
        "id_",
        [-1, None, "bad_property", 2.5],
    )
    def test_bad_property(self, id_):
        with pytest.raises(ValueError):
            ObjProperty(id_)
