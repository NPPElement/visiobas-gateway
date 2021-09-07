from .view import JsonRPCView

JSON_RPC_HANDLERS = (JsonRPCView,)

__all__ = [
    "JsonRPCView",
    "JSON_RPC_HANDLERS",
]
