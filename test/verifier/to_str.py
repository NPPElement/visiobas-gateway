import unittest

from gateway.models.bacnet import StatusFlags, ObjProperty, ObjType
from gateway.verifier import BACnetVerifier


class TestToStr(unittest.TestCase):

    def setUp(self) -> None:
        self.verifier = BACnetVerifier(protocols_queue=None,
                                       http_queue=None,
                                       mqtt_queue=None,
                                       config={}
                                       )

    def tearDown(self) -> None:
        del self.verifier

    # def test_sf_to_binary(self):
    #     pass
    #     # todo: refactor sf
    # available_status_flags = (
    #     StatusFlags([0, 0, 0, 0]),
    #     StatusFlags([0, 0, 0, 1]),
    #     StatusFlags([0, 0, 1, 0]),
    #     StatusFlags([0, 0, 1, 1]),
    #     StatusFlags([0, 1, 0, 0]),
    #     StatusFlags([0, 1, 0, 1]),
    #     StatusFlags([0, 1, 1, 0]),
    #     StatusFlags([0, 1, 1, 1]),
    #     StatusFlags([1, 0, 0, 0]),
    #     StatusFlags([1, 0, 0, 1]),
    #     StatusFlags([1, 0, 1, 0]),
    #     StatusFlags([1, 0, 1, 1]),
    #     StatusFlags([1, 1, 0, 0]),
    #     StatusFlags([1, 1, 0, 1]),
    #     StatusFlags([1, 1, 1, 0]),
    #     StatusFlags([1, 1, 1, 1]),
    # )
    # for sf, i in zip(available_status_flags, range(15, -1, -1)):
    #     with self.subTest(case=sf):
    #         self.assertEqual(sf.as_binary, i)

    def test_to_str_mqtt(self):
        dev_id = 1
        properties = {ObjProperty.objectIdentifier: 2,
                      ObjProperty.objectType: ObjType.BINARY_INPUT,
                      ObjProperty.presentValue: 4,
                      ObjProperty.statusFlags: StatusFlags()
                      }
        expected = '1 2 3 4 0'
        self.assertEqual(expected, self.verifier._to_str_mqtt(device_id=dev_id,
                                                              properties=properties
                                                              ))

    def test_to_str_http(self):
        cases = (
            {ObjProperty.objectIdentifier: 1,
             ObjProperty.objectType: ObjType.ANALOG_VALUE,
             ObjProperty.presentValue: 3,
             ObjProperty.statusFlags: StatusFlags([0, 0, 1, 0])
             },
            {ObjProperty.objectIdentifier: 2,
             ObjProperty.objectType: ObjType.BINARY_INPUT,
             ObjProperty.presentValue: 4,
             ObjProperty.statusFlags: StatusFlags([1, 0, 1, 0]),
             ObjProperty.reliability: 'error6'
             },
            {ObjProperty.objectIdentifier: 3,
             ObjProperty.objectType: ObjType.BINARY_OUTPUT,
             ObjProperty.presentValue: 5,
             ObjProperty.statusFlags: StatusFlags([0, 1, 1, 0]),
             ObjProperty.priorityArray: ('', '', '', '', '', '', '', '',
                                         '', '', '', '', '', '', '', '')
             },
            {ObjProperty.objectIdentifier: 4,
             ObjProperty.objectType: ObjType.BINARY_VALUE,
             ObjProperty.presentValue: 6,
             ObjProperty.statusFlags: StatusFlags([0, 0, 0, 1]),
             ObjProperty.priorityArray: ('', '', '', 7, '', '', '', '',
                                         '', '', '', '', '', '', '', '')
             },
            {ObjProperty.objectIdentifier: 5,
             ObjProperty.objectType: ObjType.MULTI_STATE_INPUT,  # 13
             ObjProperty.presentValue: 7,
             ObjProperty.statusFlags: StatusFlags([1, 0, 0, 1]),
             ObjProperty.priorityArray: ('', '', '', '', '', '', '', '',
                                         '', '', '', '', '', '', 8, ''),
             ObjProperty.reliability: 'error10'
             },
        )
        expected = ('1 2 3 4',
                    '2 3 4 5 error6',
                    '3 4 5 ,,,,,,,,,,,,,,, 6',
                    '4 5 6 ,,,7,,,,,,,,,,,, 8',
                    '5 13 7 ,,,,,,,,,,,,,,8, 9 error10'
                    )
        for case, exp in zip(cases, expected):
            with self.subTest(case=case):
                res = self.verifier._to_str_http(properties=case)
                self.assertEqual(res, exp)

    def test_wrongs_sf_mqtt_http(self):
        dev_id = 0
        case_mqtt = {ObjProperty.objectIdentifier: 1,
                     ObjProperty.objectType: ObjType.ANALOG_VALUE,
                     ObjProperty.presentValue: 3,
                     ObjProperty.statusFlags: StatusFlags([0, 0, 1, 0])
                     }
        case_http = {ObjProperty.objectIdentifier: 2,
                     ObjProperty.objectType: ObjType.BINARY_INPUT,
                     ObjProperty.presentValue: 4,
                     ObjProperty.statusFlags: StatusFlags([0, 0, 0, 0])
                     }

        self.assertRaises(ValueError, self.verifier._to_str_mqtt, dev_id, case_mqtt)
        self.assertRaises(ValueError, self.verifier._to_str_http, case_http)


if __name__ == '__main__':
    unittest.main()
