import pytest

from gateway.models.bacnet.obj_property import ObjProperty

MODULE_NAME = "gateway.models.bacnet.obj"


class TestBACnetObj:
    def test_construct_happy(self, bacnet_obj_factory):
        bacnet_obj = bacnet_obj_factory()
        assert bacnet_obj.resolution == 0.1
        assert bacnet_obj.reliability == "no-fault-detected"
        assert bacnet_obj.status_flags.flags == 0b0000
        assert bacnet_obj.present_value == 85.8585
        assert str(bacnet_obj.updated) == "2011-11-11 11:11:11"
        assert bacnet_obj.unreachable_in_row == 0

    def test_set_property_bad_property(self, bacnet_obj_factory):
        with pytest.raises(ValueError):
            bacnet_obj = bacnet_obj_factory()
            bacnet_obj.set_property(value="value", prop="bad_prop")

        with pytest.raises(ValueError):
            bacnet_obj = bacnet_obj_factory()
            # No property `derivativeConstant` in BACnetObj `pydantic` model.
            bacnet_obj.set_property(value="value", prop=ObjProperty.derivativeConstant)

    def test_set_property_happy(self, bacnet_obj_factory):
        bacnet_obj = bacnet_obj_factory()
        assert bacnet_obj.present_value == 85.8585
        assert str(bacnet_obj.updated) == "2011-11-11 11:11:11"

        bacnet_obj.set_property(value=58.5858, prop=ObjProperty.presentValue)
        assert bacnet_obj.present_value == 58.5858
        assert str(bacnet_obj.updated) > "2011-11-11 11:11:11"
        assert bacnet_obj.unreachable_in_row == 0

        bacnet_obj.set_property(value=2, prop=ObjProperty.statusFlags)
        assert bacnet_obj.status_flags.flags == 2
        assert bacnet_obj.unreachable_in_row == 0