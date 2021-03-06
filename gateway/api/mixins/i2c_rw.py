import busio
from adafruit_mcp230xx.mcp23008 import MCP23008
from digitalio import Direction, Pull

try:
    import board
except (ImportError, NotImplementedError) as e:
    from logging import getLogger

    _log = getLogger(__name__)
    _log.critical(f'Error: {e}',
                  exc_info=True
                  )


class I2CRWMixin:

    @staticmethod
    def read_i2c(obj_id: int, obj_type: int, dev_id: int) -> bool:
        """
        :param dev_id: in hex. Example: 0x25
        """
        dev_address = int(str(dev_id), base=16)

        # Initialize the I2C bus:
        i2c = busio.I2C(board.SCL, board.SDA)

        obj_di = MCP23008(i2c, dev_address)

        # mcp_di = MCP23008(i2c, address=0x25)
        # mcp_do = MCP23008(i2c, address=0x26)

        pin_di = obj_di.get_pin(obj_id)
        # if obj_type == ObjType.BINARY_INPUT.id:
        pin_di.direction = Direction.INPUT
        pin_di.pull = Pull.UP

        # todo obj.gpio? check on yard!

        # pins_in = [mcp_di.get_pin(i) for i in range(8)]
        # pins_out = [mcp_do.get_pin(i) for i in range(8)]
        # [pin.switch_to_output(value=True) for pin in pins_out]
        #
        # for pin in pins_in:
        #     pin.direction = digitalio.Direction.INPUT
        #     pin.pull = digitalio.Pull.UP

        # # Now loop blinking the pin 0 output and reading the state of pin 1 input.
        # while True:
        #     for pin in pins_out:
        #         pin.value = False  # горит
        #         time.sleep(0.2)
        #         pin.value = True  # гаснет

    @staticmethod
    def write_i2c(value: bool, obj_id: int, obj_type: int, dev_id: int):
        """
        :param value: True - Turn off. False - Turn on
        :param dev_id: in hex. Example: 0x25
        """
        dev_address = int(str(dev_id), base=16)

        # Initialize the I2C bus:
        i2c = busio.I2C(board.SCL, board.SDA)
        obj_do = MCP23008(i2c, dev_address)

        pin_out = obj_do.get_pin(obj_id)
        # if obj_type == ObjType.BINARY_OUTPUT.id:
        pin_out.switch_to_output(value=True)

        pin_out.value = value

    def write_with_check_i2c(self, value: bool, obj_id: int, obj_type: int, dev_id: int
                             ) -> bool:
        """
        :return: the read value is equal to the written value
        """
        self.write_i2c(value=value,
                       obj_id=obj_id,
                       obj_type=obj_type,
                       dev_id=dev_id
                       )
        rvalue = self.read_i2c(obj_id=obj_id,
                               obj_type=obj_type,
                               dev_id=dev_id
                               )
        return value == rvalue
