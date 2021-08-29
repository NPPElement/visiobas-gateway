import logging

from pymodbus.client.sync import ModbusTcpClient as ModbusClient

FORMAT = (
    "%(asctime)-15s %(threadName)-15s "
    "%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s"
)
logging.basicConfig(format=FORMAT)
_log = logging.getLogger()
_log.setLevel(logging.INFO)

UNIT = 0x1

client = ModbusClient("localhost", port=5020)
client.connect()


# _log.info("Reading Coils")
# rr = client.read_coils(1, 1, unit=UNIT)
# _log.info(f'{rr} isError:{rr.isError()} bits:{rr.bits}')
# _log.info("Write to a Coil and read back")
# rq = client.write_coil(0, True, unit=UNIT)
# rr = client.read_coils(0, 1, unit=UNIT)
# assert (not rq.isError())  # test that we are not an error
# assert (rr.bits[0] == True)  # test the expected value
#
# _log.info("Write to multiple coils and read back- test 1")
# rq = client.write_coils(1, [True] * 8, unit=UNIT)
# assert (not rq.isError())  # test that we are not an error
# rr = client.read_coils(1, 21, unit=UNIT)
# assert (not rr.isError())  # test that we are not an error
# resp = [True] * 21

# If the returned output quantity is not a multiple of eight,
# the remaining bits in the final data byte will be padded with zeros
# (toward the high order end of the byte).

# resp.extend([False] * 3)
# assert (rr.bits == resp)  # test the expected value
#
# _log.info("Write to multiple coils and read back - test 2")
# rq = client.write_coils(1, [False] * 8, unit=UNIT)
# rr = client.read_coils(1, 8, unit=UNIT)
# assert (not rq.isError())  # test that we are not an error
# assert (rr.bits == [False] * 8)  # test the expected value
#
# _log.info("Read discrete inputs")
# rr = client.read_discrete_inputs(0, 8, unit=UNIT)
# assert (not rq.isError())  # test that we are not an error

_log.info("Write to a holding register and read back")
# rq = client.write_register(1, 10, unit=UNIT)
rr = client.read_holding_registers(0, 33, unit=UNIT)
# assert (not rq.isError())  # test that we are not an error
# assert (rr.registers[0] == 10)  # test the expected value
_log.info(f"{rr} isError:{rr.isError()} registers:{rr.registers}")

_log.info("Write to multiple holding registers and read back")
rq = client.write_registers(1, [10] * 8, unit=UNIT)
rr = client.read_holding_registers(1, 8, unit=UNIT)
assert not rq.isError()  # test that we are not an error
assert rr.registers == [10] * 8  # test the expected value

_log.info("Read input registers")
rr = client.read_input_registers(1, 8, unit=UNIT)
assert not rq.isError()  # test that we are not an error

arguments = {
    "read_address": 1,
    "read_count": 8,
    "write_address": 1,
    "write_registers": [20] * 8,
}
_log.info("Read write registeres simulataneously")
rq = client.readwrite_registers(unit=UNIT, **arguments)
rr = client.read_holding_registers(1, 8, unit=UNIT)
assert not rq.isError()  # test that we are not an error
assert rq.registers == [20] * 8  # test the expected value
assert rr.registers == [20] * 8  # test the expected value

# ----------------------------------------------------------------------- #
# close the client
# ----------------------------------------------------------------------- #
client.close()
