# from .base import BaseView
from .jsonrpc import JsonRPCView
from .rest import PropertyView

HANDLERS = (JsonRPCView,
            PropertyView
            )

__all__ = (  # 'BaseView',
           'JsonRPCView',
           'PropertyView',
           'HANDLERS'
           )
