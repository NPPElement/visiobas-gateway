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
    def test__get_chunk_for_multiple_without_breaks(
        self, modbus_obj_factory, register_sequence, quantity, objs_per_chunks
    ):
        objs = [
            modbus_obj_factory(address=register, quantity=quantity)
            for register in register_sequence
        ]
        assert len(list(ModbusDevice._get_chunk_for_multiple(objs=objs))) == len(
            objs_per_chunks
        )
        for chunk, chunk_len in zip(
            ModbusDevice._get_chunk_for_multiple(objs=objs), objs_per_chunks
        ):
            assert len(chunk) == chunk_len

    @pytest.mark.parametrize(
        "register_sequence, quantity, objs_per_chunks",
        [
            ([*list(range(0, 66)), *list(range(166, 199))], 1, (66, 33)),
            ([*list(range(0, 20, 2)), *list(range(40, 60, 2))], 2, (10, 10)),
            ([*list(range(0, 225)), *list(range(333, 366))], 1, (125, 100, 33)),
            ([*list(range(0, 13, 3))], 1, (1, 1, 1, 1, 1)),
        ],
    )
    def test__get_chunk_for_multiple_with_breaks(
        self, modbus_obj_factory, register_sequence, quantity, objs_per_chunks
    ):
        objs = [
            modbus_obj_factory(address=register, quantity=quantity)
            for register in register_sequence
        ]
        assert len(list(ModbusDevice._get_chunk_for_multiple(objs=objs))) == len(
            objs_per_chunks
        )
        for chunk, chunk_len in zip(
            ModbusDevice._get_chunk_for_multiple(objs=objs), objs_per_chunks
        ):
            assert len(chunk) == chunk_len
