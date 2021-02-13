from aiohttp.web_urldispatcher import View


class BaseView(View):
    @property
    def gateway(self):  # -> VisioGateway
        return self.request.app['gateway']
