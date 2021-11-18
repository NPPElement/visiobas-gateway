from visiobas_gateway.devices.bacnet.bacnet import BACnetDevice
import pytest


class TestBACnetDevice:
    @pytest.mark.parametrize(
        "objs_len, objs_per_chunks",
        [(78, (25, 25, 25, 3)), (257, (25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 7))],
    )
    def test__get_chunk_for_multiple(self, bacnet_obj_factory, objs_len, objs_per_chunks):
        objs = [bacnet_obj_factory()] * objs_len

        for chunk, chunk_len in zip(
            BACnetDevice._get_chunk_for_multiple(objs=objs), objs_per_chunks
        ):
            assert len(chunk) == chunk_len
