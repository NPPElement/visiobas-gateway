from gateway.models.modbus import ModbusObjModel


data_dict = {'103': 'no-fault-detected',
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
             '28': 'Температура в помещении трансформатора 2.',
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
             '371': '{"template":"","alias":"TEMP_TR2","replace":{},"modbus":{"address":1007,"quantity":2,"functionRead":"0x04","dataType":"FLOAT","dataLenght":32,"scale":10}}',
             '45': None,
             '52': None,
             '59': None,
             '65': None,
             '69': None,
             '72': None,
             '75': 496,
             '77': 'Site:Engineering/Electricity.TP_1002.Temperature.AI_703',
             '79': 'binary-input',
             '81': None,
             '846': 1673,
             '85': 0.0,
             'timestamp': '2021-02-04 05:47:23'}

obj = ModbusObjModel(**data_dict)

print(obj.dict())
