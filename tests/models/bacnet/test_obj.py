import unittest

from gateway.models.bacnet import BACnetObj


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.AI_obj.set_pv(value=12345.67890)
        self.assertEqual(self.AI_obj.pv, 12345.7)

    def setUp(self) -> None:
        raw_AI_obj_data = {
            "103": None,
            "106": 0.1,
            "111": [False, True, False, False],
            "113": None,
            "117": None,
            "118": None,
            "130": None,
            "133": False,
            "168": None,
            "17": None,
            "22": None,
            "25": None,
            "28": "deleted",
            "31": None,
            "35": [False, False, False],
            "351": None,
            "352": None,
            "353": None,
            "354": None,
            "355": None,
            "356": None,
            "357": None,
            "36": None,
            "371": {
                "template": "",
                "alias": "",
                "replace": {},
                "modbus": {
                    "address": 46,
                    "quantity": 2,
                    "functionRead": "0x03",
                    "dataType": "float",
                    "dataLength": 32,
                    "scale": 1,
                    "wordOrder": "big",
                    "byteOrder": "big",
                },
            },
            "45": None,
            "52": None,
            "59": None,
            "65": None,
            "69": None,
            "72": None,
            "75": 22,
            "77": "deleted",
            "79": "analog-input",
            "81": None,
            "846": 4004,
            "85": 2.3,
            "885": 0,
            "timestamp": "2021-05-29 17:59:20",
        }
        self.AI_obj = BACnetObj(**raw_AI_obj_data)


if __name__ == "__main__":
    unittest.main()
