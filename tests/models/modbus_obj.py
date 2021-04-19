import unittest

from gateway.models.modbus import ModbusObjModel


class TestToStr(unittest.TestCase):
    def setUp(self) -> None:
        self._set_AI_BI_objects_data()

    def test_parse(self):
        ai_obj = ModbusObjModel(**self.AI_obj_data)
        bi_obj = ModbusObjModel(**self.BI_obj_data)

        print(ai_obj, bi_obj, sep='\n')

    def test_(self):
        pass  # todo

    def _set_AI_BI_objects_data(self) -> None:
        self.AI_obj_data = {'103': 'no-fault-detected',
                            '106': None,
                            '111': [False, True, False, False],
                            '113': None,
                            '117': None,
                            '118': None,
                            '130': None,
                            '133': True,
                            '168': None,
                            '17': None,
                            '22': 1.0,
                            '25': None,
                            '28': 'deleted',
                            '31': None,
                            '35': [False, False, False],
                            '351': None,
                            '352': None,
                            '353': None,
                            '354': None,
                            '355': None,
                            '356': None,
                            '357': None,
                            '36': None,
                            '371': '{"template":"","alias":"deleted","replace":{},"modbus":{"address":203,"quantity":1,"functionRead":"0x03","dataType":"INT","dataLenght":16,"scale":1}}',
                            '45': None,
                            '52': None,
                            '59': None,
                            '65': None,
                            '69': None,
                            '72': None,
                            '75': 363,
                            '77': 'deleted',
                            '79': 'analog-input',
                            '81': None,
                            '846': 1111,
                            '85': 0.0,
                            'timestamp': 'deleted'}
        self.BI_obj_data = {'103': 'no-fault-detected',
                            '106': None,
                            '111': [False, True, False, False],
                            '113': None,
                            '117': None,
                            '118': None,
                            '130': None,
                            '133': True,
                            '168': None,
                            '17': None,
                            '22': 0.1,
                            '25': None,
                            '28': 'deleted',
                            '31': None,
                            '35': [False, False, False],
                            '351': None,
                            '352': None,
                            '353': None,
                            '354': None,
                            '355': None,
                            '356': None,
                            '357': None,
                            '36': None,
                            '371': '{"template":"","alias":"deleted","replace":{},"modbus":{"address":1007,"quantity":2,"functionRead":"0x04","dataType":"FLOAT","dataLenght":32,"scale":10}}',
                            '45': None,
                            '52': None,
                            '59': None,
                            '65': None,
                            '69': None,
                            '72': None,
                            '75': 496,
                            '77': 'deleted',
                            '79': 'binary-input',
                            '81': None,
                            '846': 1111,
                            '85': 0.0,
                            'timestamp': 'deleted'}
