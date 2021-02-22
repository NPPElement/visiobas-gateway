import unittest

from bacpypes.basetypes import PriorityArray, PriorityValue
from bacpypes.primitivedata import Null

from gateway.models.bacnet import ObjType, ObjProperty, StatusFlag
from gateway.verifier import BACnetVerifier


class TestVerify(unittest.TestCase):
    def setUp(self) -> None:
        self.verifier = BACnetVerifier(protocols_queue=None,
                                       http_queue=None,
                                       mqtt_queue=None,
                                       config={}
                                       )

    def tearDown(self) -> None:
        del self.verifier

    def test_verify_unfilled(self):
        cases = (
            {},
            {ObjProperty.objectType: ObjType.ANALOG_INPUT},
            {ObjProperty.objectIdentifier: 13},
            {ObjProperty.presentValue: 666.0},
            {ObjProperty.objectIdentifier: 13, ObjProperty.presentValue: 666.0},
            {ObjProperty.objectType: ObjType.ANALOG_INPUT, ObjProperty.presentValue: 666.0}
        )
        for case in cases:
            with self.subTest(case=case):
                self.assertRaises(KeyError, self.verifier.verify, case)

    def test_verify_simple_correct(self):
        cases = (
            {ObjProperty.objectType: ObjType.ANALOG_INPUT,
             ObjProperty.objectIdentifier: 1,
             ObjProperty.presentValue: 1
             },
            {ObjProperty.objectType: ObjType.ANALOG_INPUT,
             ObjProperty.objectIdentifier: 2,
             ObjProperty.presentValue: 2,
             ObjProperty.reliability: 2
             },
            {ObjProperty.objectType: ObjType.ANALOG_INPUT,
             ObjProperty.objectIdentifier: 3,
             ObjProperty.presentValue: 3,
             ObjProperty.reliability: 3,
             ObjProperty.statusFlags: 0
             },
            {ObjProperty.objectType: ObjType.ANALOG_INPUT,
             ObjProperty.objectIdentifier: 4,
             ObjProperty.presentValue: 4,
             ObjProperty.reliability: 4,
             ObjProperty.statusFlags: StatusFlag.OVERRIDEN.value
             }
        )
        expected = (
            {ObjProperty.objectType: ObjType.ANALOG_INPUT,
             ObjProperty.objectIdentifier: 1,
             ObjProperty.statusFlags: 0,
             ObjProperty.reliability: 0,
             ObjProperty.presentValue: 1,
             },
            {ObjProperty.objectType: ObjType.ANALOG_INPUT,
             ObjProperty.objectIdentifier: 2,
             ObjProperty.presentValue: 2,
             ObjProperty.statusFlags: 0,
             ObjProperty.reliability: 2
             },
            {ObjProperty.objectType: ObjType.ANALOG_INPUT,
             ObjProperty.objectIdentifier: 3,
             ObjProperty.presentValue: 3,
             ObjProperty.reliability: 3,
             ObjProperty.statusFlags: 0
             },
            {ObjProperty.objectType: ObjType.ANALOG_INPUT,
             ObjProperty.objectIdentifier: 4,
             ObjProperty.presentValue: 4,
             ObjProperty.reliability: 4,
             ObjProperty.statusFlags: StatusFlag.OVERRIDEN.value
             }
        )
        for case, _expected in zip(cases, expected):
            with self.subTest(case=case):
                _result = self.verifier.verify(obj_properties=case)
                self.assertDictEqual(_expected, _result)

    def test_verify_binary(self):
        cases = (
            {ObjProperty.objectType: ObjType.BINARY_INPUT,
             ObjProperty.objectIdentifier: 1,
             ObjProperty.presentValue: 'active'
             },
            {ObjProperty.objectType: ObjType.BINARY_INPUT,
             ObjProperty.objectIdentifier: 2,
             ObjProperty.presentValue: 'inactive',
             ObjProperty.reliability: 2,
             ObjProperty.statusFlags: 0
             }
        )
        expected = (
            {ObjProperty.objectType: ObjType.BINARY_INPUT,
             ObjProperty.objectIdentifier: 1,
             ObjProperty.statusFlags: 0,
             ObjProperty.reliability: 0,
             ObjProperty.presentValue: 1,
             },
            {ObjProperty.objectType: ObjType.BINARY_INPUT,
             ObjProperty.objectIdentifier: 2,
             ObjProperty.presentValue: 0,
             ObjProperty.statusFlags: 0,
             ObjProperty.reliability: 2
             }
        )
        for case, _expected in zip(cases, expected):
            with self.subTest(case=case):
                _result = self.verifier.verify(obj_properties=case)
                self.assertDictEqual(_expected, _result)

    def test_verify_with_priority_array(self):
        cases = (
            {ObjProperty.objectType: ObjType.ANALOG_VALUE,
             ObjProperty.objectIdentifier: 1,
             ObjProperty.presentValue: 1,
             ObjProperty.priorityArray: PriorityArray(
                 [PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null())])
             },
            {ObjProperty.objectType: ObjType.MULTI_STATE_OUTPUT,
             ObjProperty.objectIdentifier: 2,
             ObjProperty.presentValue: 2.,
             ObjProperty.reliability: 2,
             ObjProperty.priorityArray: PriorityArray(
                 [PriorityValue(null=Null()), PriorityValue(real=2.2),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null())])
             },
            {ObjProperty.objectType: ObjType.BINARY_OUTPUT,
             ObjProperty.objectIdentifier: 3,
             ObjProperty.presentValue: 3.,
             ObjProperty.priorityArray: PriorityArray(
                 [PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(real=3.3),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null()),
                  PriorityValue(null=Null()), PriorityValue(null=Null())])
             }
        )

        expected = (
            {ObjProperty.objectType: ObjType.ANALOG_VALUE,
             ObjProperty.objectIdentifier: 1,
             ObjProperty.statusFlags: 0,
             ObjProperty.reliability: 0,
             ObjProperty.presentValue: 1,
             ObjProperty.priorityArray: ('', '', '', '', '', '', '', '',
                                         '', '', '', '', '', '', '', '')
             },
            {ObjProperty.objectType: ObjType.MULTI_STATE_OUTPUT,
             ObjProperty.objectIdentifier: 2,
             ObjProperty.presentValue: 2.,
             ObjProperty.statusFlags: 0,
             ObjProperty.reliability: 2,
             ObjProperty.priorityArray: ('', 2, '', '', '', '', '', '',
                                         '', '', '', '', '', '', '', '')
             },
            {ObjProperty.objectType: ObjType.BINARY_OUTPUT,
             ObjProperty.objectIdentifier: 3,
             ObjProperty.presentValue: 3.,
             ObjProperty.statusFlags: StatusFlag.FAULT.value,
             ObjProperty.reliability: 0,
             ObjProperty.priorityArray: ('', '', '', '', '', '', '', 3,
                                         '', '', '', '', '', '', '', '')
             }
        )
        for case, _expected in zip(cases, expected):
            with self.subTest(case=case):
                _result = self.verifier.verify(obj_properties=case)
                print(f'Res: {_result}', f"Exp: {_expected}", sep='\n')
                self.assertDictEqual(_expected, _result)


if __name__ == '__main__':
    unittest.main()
