from json import loads
from multiprocessing import SimpleQueue
from pathlib import Path

from gateway.connectors import Connector
from gateway.connectors.bacnet import ObjProperty, ObjType, BACnetObj
from gateway.connectors.modbus import ModbusObj, VisioModbusProperties
from gateway.connectors.modbus.device import ModbusDevice
from gateway.logs import get_file_logger

_base_path = Path(__file__).resolve().parent.parent.parent

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class ModbusConnector(Connector):
    # __slots__ = ('_config', 'default_update_period', '_gateway', '_verifier_queue',
    #              '_connected', '_stopped', 'obj_types_to_request',
    #              'address_cache', 'polling_devices', '_update_intervals'
    #              )

    def __init__(self, gateway, http_queue: SimpleQueue,
                 verifier_queue: SimpleQueue, config: dict):

        super().__init__(gateway=gateway,
                         http_queue=http_queue,
                         verifier_queue=verifier_queue,
                         config=config
                         )

        self.obj_types_to_request = (
            ObjType.ANALOG_INPUT, ObjType.ANALOG_OUTPUT, ObjType.ANALOG_VALUE,
            ObjType.BINARY_INPUT, ObjType.BINARY_OUTPUT, ObjType.BINARY_VALUE,
            ObjType.MULTI_STATE_INPUT, ObjType.MULTI_STATE_OUTPUT,
            ObjType.MULTI_STATE_VALUE,
        )

    def __repr__(self):
        return 'ModbusConnector'

    def run(self):
        _log.info(f'{self} starting ...')
        while not self._stopped:
            try:
                # Requesting objects and their types from the server.
                # Then stop received device (if need) and start updated.
                self.run_update_devices_loop()
            except Exception as e:
                _log.error(f'Device update error: {e}',
                           exc_info=True
                           )
        else:
            _log.info(f'{self} stopped.')

    def start_device(self, device_id: int, objs: set[ModbusObj],
                     upd_interval: int) -> None:
        """Start Modbus device thread."""
        _log.debug(f'Starting Device [{device_id}] ...')
        try:
            self.polling_devices[device_id] = ModbusDevice(
                verifier_queue=self._verifier_queue,
                connector=self,
                address=self.address_cache[device_id],
                device_id=device_id,
                objects=objs,
                update_period=upd_interval
            )
            _log.info(f'Device [{device_id}] started')
        # except ConnectionError as e:
        #     _log.error(f'Device [{device_id}] connection error: {e}')
        #     self.__not_connect_devices.add(device_id)
        except Exception as e:
            _log.error(f'Device [{device_id}] starting error: {e}',
                       exc_info=True
                       )

    def parse_objs_data(self, objs_data: dict[ObjType, list[dict]]
                        ) -> tuple[int, set[BACnetObj]]:
        """"""
        # Extract update period
        upd_period = self.parse_upd_period(device_obj_data=objs_data[ObjType.DEVICE])

        modbus_objs = set()
        # Create protocol objects from objs_data
        for obj_type, objs in objs_data.items():
            for obj in objs:
                try:
                    obj_id = obj[str(ObjProperty.objectIdentifier.id)]
                    obj_name = obj[str(ObjProperty.objectName.id)]

                    prop_list = obj[str(ObjProperty.propertyList.id)]
                    address, quantity, func_read, props = self.parse_modbus_properties(
                        property_list=prop_list)
                    modbus_obj = ModbusObj(typename='ModbusObject',
                                           type=obj_type,
                                           id=obj_id,
                                           name=obj_name,

                                           address=address,
                                           quantity=quantity,
                                           func_read=func_read,

                                           properties=props
                                           )
                    modbus_objs.add(modbus_obj)
                except (LookupError, Exception) as e:
                    _log.warning(f'Extract object error: {e}',
                                 exc_info=True
                                 )
        return upd_period, modbus_objs

    @staticmethod
    def parse_modbus_properties(property_list: str
                                ) -> tuple[int, int, int, VisioModbusProperties]:
        try:
            modbus_properties = loads(property_list)['modbus']

            address = int(modbus_properties['address'])
            quantity = int(modbus_properties['quantity'])
            func_read = int(modbus_properties['functionRead'][-2:])

            scale = int(modbus_properties.get('scale', 1))
            data_type = modbus_properties['dataType']
            data_length = modbus_properties.get('dataLength', None)
            bit = modbus_properties.get('bit', None)

            # byte_order = '<' if quantity == 1 else '>'
            # byte_order = None  # don't use now # todo

            # trying to fill the data if it is not enough
            if data_type == 'BOOL' and bit is None and data_length is None:
                data_length = 16
            elif data_type == 'BOOL' and isinstance(bit, int) and data_length is None:
                data_length = 1
            elif data_type != 'BOOL' and data_length is None and isinstance(quantity, int):
                data_length = quantity * 16

            properties = VisioModbusProperties(scale=scale,
                                               data_type=data_type,
                                               data_length=data_length,
                                               # byte_order=byte_order,
                                               bit=bit
                                               )
            _log.debug(f'Received: {modbus_properties}\n'
                       f'Extracted properties: {properties}')
        except (LookupError, Exception) as e:
            _log.warning('Modbus property cannot be extracted')
            raise e
        else:
            return address, quantity, func_read, properties
