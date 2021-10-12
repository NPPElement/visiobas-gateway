import pytest

from visiobas_gateway.schemas.protocol import Protocol


class TestProtocol:
    @pytest.mark.parametrize(
        "protocol",
        [
            "BACnet",
            "ModbusTCP",
            "ModbusRTU",
            "ModbusRTUoverTCP",
        ],
    )
    def test_construct_happy(self, protocol):
        assert Protocol(protocol).value == protocol

    @pytest.mark.parametrize(
        "bad_protocol",
        [
            "bad_protocol",
            "123",
            "None",
            321,
        ],
    )
    def test_construct_bad_protocol(self, bad_protocol):
        with pytest.raises(ValueError):
            Protocol(bad_protocol)
