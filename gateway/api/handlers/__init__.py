from .jsonrpc import JsonRPCView
from .property import ModbusPropertyView

HANDLERS = (JsonRPCView,
            ModbusPropertyView
            )
