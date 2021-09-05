from gateway.models.bacnet.status_flags import StatusFlags


class TestBACnetObj:
    def test_construct_happy(self, bacnet_obj_factory):
        bacnet_obj = bacnet_obj_factory()
        assert bacnet_obj.resolution == 0.1
        assert bacnet_obj.reliability == "no-fault-detected"
        assert bacnet_obj.status_flags == StatusFlags(flags=0)
        assert bacnet_obj.present_value == 85.8585
        assert str(bacnet_obj.updated) == "2011-11-11 11:11:11"
