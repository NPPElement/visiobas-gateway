from .base import BaseView
from .jsonrpc import JsonRPCView
from .mixins import ModbusRWMixin
from .rest import ModbusPropertyView

HANDLERS = (JsonRPCView,
            ModbusPropertyView
            )

__all__ = ('BaseView',
           'ModbusRWMixin',
           'JsonRPCView',
           'ModbusPropertyView',
           'HANDLERS'
           )
