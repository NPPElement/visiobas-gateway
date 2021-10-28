from ..base_view import BaseView
from ...utils import get_file_logger, log_exceptions
from aiohttp import web
from ...utils.monitor import get_monitor_info, MONITOR_COMMANDS

_LOG = get_file_logger(name=__name__)


class RESTMonitorView(BaseView):
    URL_PATH = r'/monitor'

    @log_exceptions(logger=_LOG)
    async def get(self) -> web.StreamResponse:
        monitor_info = await get_monitor_info(cmds=MONITOR_COMMANDS)

        return web.json_response(
            monitor_info.json()
        )
