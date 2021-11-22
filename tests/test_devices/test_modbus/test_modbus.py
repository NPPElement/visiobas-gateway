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

    @pytest.mark.parametrize(
        "register_sequence, quantities, objs_per_chunks",
        [
            ((range(0, 22, 1), range(22, 44, 2)), (1, 2), (33,)),
            ((range(0, 22, 1), range(22, 44, 2), range(44, 88, 4)), (1, 2, 4), (44,)),
            ((range(0, 22, 1), range(22, 44, 2), range(44, 128, 8)), (1, 2, 8), (43, 1)),
        ],
    )
    def test__get_chunk_for_multiple_different_register_length(
        self, modbus_obj_factory, register_sequence, quantities, objs_per_chunks
    ):
        objs = []
        for registers_range, quantity in zip(register_sequence, quantities):
            objs.extend(
                [
                    modbus_obj_factory(address=register, quantity=quantity)
                    for register in registers_range
                ]
            )

        assert len(list(ModbusDevice._get_chunk_for_multiple(objs=objs))) == len(
            objs_per_chunks
        )
        for chunk, chunk_len in zip(
            ModbusDevice._get_chunk_for_multiple(objs=objs), objs_per_chunks
        ):
            assert len(chunk) == chunk_len

    @pytest.mark.parametrize(
        "register_sequence, read_funcs, objs_per_chunks",
        [
            ((range(0, 11), range(11, 22)), ("0x03", "0x04"), (11, 11)),
            (
                (range(0, 5), range(5, 11), range(11, 22)),
                ("0x03", "0x03", "0x04"),
                (11, 11),
            ),
        ],
    )
    def test__get_chunk_for_multiple_different_read_func(
        self, modbus_obj_factory, register_sequence, read_funcs, objs_per_chunks
    ):
        objs = []
        for registers_range, read_func in zip(register_sequence, read_funcs):
            objs.extend(
                [
                    modbus_obj_factory(address=register, quantity=1, functionRead=read_func)
                    for register in registers_range
                ]
            )

        assert len(list(ModbusDevice._get_chunk_for_multiple(objs=objs))) == len(
            objs_per_chunks
        )
        for chunk, chunk_len in zip(
            ModbusDevice._get_chunk_for_multiple(objs=objs), objs_per_chunks
        ):
            assert len(chunk) == chunk_len
