from .base import BaseView
from .jsonrpc import JsonRPCView
from .rest import ModbusPropertyView

HANDLERS = (JsonRPCView,
            ModbusPropertyView
            )

__all__ = ('BaseView',
           'JsonRPCView',
           'ModbusPropertyView',
           'HANDLERS'
           )
