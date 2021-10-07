from typing import Any

from ...schemas.bacnet.device_property_list import TcpIpDevicePropertyList
from ..base_device import BaseDevice


class SUNAPIDevice(BaseDevice):
    """Now used for XNP-6550-RH."""

    def ptz(self, cgi: str, submenu: str, action: str, **kwargs: Any) -> None:
        """The absolute submenu of `ptzcontrol.cgi` controls absolute a PTZ operation
        that moves the camera to the specified position.

        # todo: add check
        """
        assert isinstance(self._device_obj.property_list, TcpIpDevicePropertyList)

        control_submenus = {
            "absolute",
            "relative",
            "continuous",
            "query",
            "preset",
            "swing",
            "group",
            "tour",
            "trace",
            "home",
            "areazoom",
            "stop",
            "move",
            "aux",
            "digitalautotracking",
            "rs485Command",
            "osdmenu",
        }
        config_submenus = {
            "swing",
            "group",
            "tour",
            "trace",
            "autorun",
            "home",
            "preset",
            "presetimageconfig",
            "presetvideoanalysis",
            "Presetvideoanalysis2",
            "ptzsettings",
        }
        # actions = {}  # todo

        if cgi == "control":
            if submenu not in control_submenus:
                raise ValueError(f"Control submenu must be one of {control_submenus}")
        elif cgi == "config":
            if submenu not in config_submenus:
                raise ValueError(f"Config submenu must be one of {config_submenus}")
        else:
            raise ValueError("Provide `control` or `config` cgi")

        cgi = "ptz" + cgi + ".cgi"
        url_path = f"http://{self._device_obj.property_list.address}/stw‐cgi/{cgi}"
        # ex = 'http://<Device IP>/stw‐cgi/ptzcontrol.cgi?
        # msubmenu=absolute&action=control&Pan=90&Zoom=30&Tilt=25'
        if self._gtw.http_client is not None:
            self._gtw.http_client.request(
                method="POST",
                url=url_path,
                params={"msubmenu": submenu, "action": action, **kwargs},
            )
