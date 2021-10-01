from visiobas_gateway.schemas.modbus.func_code import ModbusReadFunc, ModbusWriteFunc
from visiobas_gateway.schemas.modbus.data_type import ModbusDataType
from visiobas_gateway.schemas.modbus.endian import Endian


class TestModbusProperties:
    def test_construct_happy(self, modbus_properties_factory):
        float32_modbus_properties = modbus_properties_factory()
        assert float32_modbus_properties.address == 11
        assert float32_modbus_properties.func_read == ModbusReadFunc.READ_INPUT_REGISTERS
        assert float32_modbus_properties.func_write == ModbusWriteFunc.WRITE_REGISTER
        assert float32_modbus_properties.quantity == 2
        assert float32_modbus_properties.scale == 10
        assert float32_modbus_properties.offset == 0
        assert float32_modbus_properties.data_type == ModbusDataType.FLOAT
        assert float32_modbus_properties.data_length == 32
        assert float32_modbus_properties.byte_order == Endian.LITTLE
        assert float32_modbus_properties.word_order == Endian.LITTLE
        assert float32_modbus_properties.bit is None
