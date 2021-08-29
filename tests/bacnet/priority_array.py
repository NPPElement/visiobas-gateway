import unittest

from bacpypes.basetypes import PriorityArray, PriorityValue
from bacpypes.primitivedata import Null

from gateway.connectors.bacnet.device import BACnetDevice


class TestPriorityArrayCast(unittest.TestCase):
    def test_to_tuple_nulls(self):
        pa = PriorityArray(
            [
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
            ]
        )
        expected = (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        self.assertTupleEqual(expected, BACnetDevice.pa_to_tuple(pa=pa))

    def test_to_tuple_with_value(self):
        pa = PriorityArray(
            [
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(real=3.3),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
                PriorityValue(null=Null()),
            ]
        )
        expected = (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            3.3,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        self.assertTupleEqual(expected, BACnetDevice.pa_to_tuple(pa=pa))


if __name__ == "__main__":
    unittest.main()
