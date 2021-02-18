from .base import BaseView
from .jsonrpc import JsonRPCView
from .mixins import ModbusMixin
from .rest import ModbusPropertyView

HANDLERS = (JsonRPCView,
            ModbusPropertyView
            )

__all__ = ('BaseView',
           'ModbusMixin',
           'JsonRPCView',
           'ModbusPropertyView',
           'HANDLERS'
           )
