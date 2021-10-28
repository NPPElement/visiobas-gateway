from aiohttp import web

from ...utils import get_file_logger, log_exceptions
from ...utils.monitor import MONITOR_COMMANDS, get_monitor_info
from ..base_view import BaseView

_LOG = get_file_logger(name=__name__)


class RESTMonitorView(BaseView):
    """View to provide access to system information."""

    URL_PATH = r"/monitor"

    @log_exceptions(logger=_LOG)
    async def get(self) -> web.StreamResponse:
        monitor_info = await get_monitor_info(cmds=MONITOR_COMMANDS)

        return web.json_response(monitor_info.json())
