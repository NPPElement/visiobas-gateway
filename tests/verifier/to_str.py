# import unittest
#
# from visiobas_gateway.schemas.bacnet import StatusFlag, ObjProperty, ObjType
# from visiobas_gateway.verifier import BACnetVerifier
#
#
# class TestToStr(unittest.TestCase):
#
#     def test_to_str_mqtt(self):
#         dev_id = 1
#         properties = {ObjProperty.objectIdentifier: 2,
#                       ObjProperty.objectType: ObjType.BINARY_INPUT,
#                       ObjProperty.presentValue: 4,
#                       ObjProperty.statusFlags: 0b0000
#                       }
#         expected = '1 2 3 4 0'
#         self.assertEqual(expected, BACnetVerifier._to_str_mqtt(device_id=dev_id,
#                                                                properties=properties
#                                                                ))
#
#     def test_to_str_http(self):
#         cases = (
#             {ObjProperty.objectIdentifier: 1,
#              ObjProperty.objectType: ObjType.ANALOG_VALUE,
#              ObjProperty.presentValue: 3,
#              ObjProperty.statusFlags: StatusFlag.OVERRIDEN.value
#              },
#             {ObjProperty.objectIdentifier: 2,
#              ObjProperty.objectType: ObjType.BINARY_INPUT,
#              ObjProperty.presentValue: 4,
#              ObjProperty.statusFlags: StatusFlag.OVERRIDEN.value | StatusFlag.IN_ALARM.value,
#              ObjProperty.reliability: 'error6'
#              },
#             {ObjProperty.objectIdentifier: 3,
#              ObjProperty.objectType: ObjType.BINARY_OUTPUT,
#              ObjProperty.presentValue: 5,
#              ObjProperty.statusFlags: StatusFlag.FAULT.value | StatusFlag.OVERRIDEN.value,
#              ObjProperty.priorityArray: (None, None, None, None, None, None, None, None,
#                                          None, None, None, None, None, None, None, None,)
#              },
#             {ObjProperty.objectIdentifier: 4,
#              ObjProperty.objectType: ObjType.BINARY_VALUE,
#              ObjProperty.presentValue: 6,
#              ObjProperty.priorityArray: (None, None, None, 7, None, None, None, None,
#                                          None, None, None, None, None, None, None, None,),
#              ObjProperty.statusFlags: StatusFlag.OUT_OF_SERVICE.value,
#              },
#             {ObjProperty.objectIdentifier: 5,
#              ObjProperty.objectType: ObjType.MULTI_STATE_INPUT,  # 13
#              ObjProperty.presentValue: 7,
#              ObjProperty.priorityArray: (None, None, None, None, None, None, None, None,
#                                          None, None, None, None, None, None, 8, None,),
#              ObjProperty.statusFlags: StatusFlag.OUT_OF_SERVICE.value | StatusFlag.IN_ALARM.value,
#              ObjProperty.reliability: 'error10'
#              },
#         )
#         expected = ('1 2 3 4',
#                     '2 3 4 5 error6',
#                     '3 4 5 ,,,,,,,,,,,,,,, 6',
#                     '4 5 6 ,,,7,,,,,,,,,,,, 8',
#                     '5 13 7 ,,,,,,,,,,,,,,8, 9 error10'
#                     )
#         for case, exp in zip(cases, expected):
#             with self.subTest(case=case):
#                 res = BACnetVerifier._to_str_http(properties=case)
#                 self.assertEqual(res, exp)
#
#     # def test_wrongs_sf_mqtt_http(self):
#     #     dev_id = 0
#     #     case_mqtt = {ObjProperty.objectIdentifier: 1,
#     #                  ObjProperty.objectType: ObjType.ANALOG_VALUE,
#     #                  ObjProperty.presentValue: 3,
#     #                  ObjProperty.statusFlags: StatusFlag.FAULT.value
#     #                  }
#     #     case_http = {ObjProperty.objectIdentifier: 2,
#     #                  ObjProperty.objectType: ObjType.BINARY_INPUT,
#     #                  ObjProperty.presentValue: 4,
#     #                  ObjProperty.statusFlags: 0b0000
#     #                  }
#     #
#     #     self.assertRaises(ValueError, BACnetVerifier._to_str_mqtt, dev_id, case_mqtt)
#     #     self.assertRaises(ValueError, BACnetVerifier._to_str_http, case_http)
#
#
# if __name__ == '__main__':
#     unittest.main()
