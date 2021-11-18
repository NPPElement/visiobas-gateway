from visiobas_gateway.devices.modbus.modbus import ModbusDevice
import pytest


class TestModbusDevice:
    @pytest.mark.parametrize(
        "register_sequence, quantity, objs_per_chunks",
        [
            (range(0, 334, 2), 2, (62, 62, 43)),
            (range(133), 1, (125, 8)),
        ],
    )
    def test__get_chunk_for_multiple(
        self, modbus_obj_factory, register_sequence, quantity, objs_per_chunks
    ):
        objs = [
            modbus_obj_factory(address=register, quantity=quantity)
            for register in register_sequence
        ]
        for chunk, chunk_len in zip(
            ModbusDevice._get_chunk_for_multiple(objs=objs), objs_per_chunks
        ):
            assert len(chunk) == chunk_len
