from typing import Callable, Any

from gateway.models.bacnet.base_obj import BaseBACnetObj

import pytest


@pytest.fixture
def base_bacnet_obj_factory() -> Callable[..., BaseBACnetObj]:
    """
    Produces `BaseBACnetObj` for tests.

    You can pass the same params into this as the `BaseBACnetObj` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _base_bacnet_obj_kwargs(kwargs)
        return BaseBACnetObj(**kwargs)

    return _factory


def _base_bacnet_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "75": 75,
        "77": "Name:Name/Name.Name",
        "79": "analog-input",
        "371": {
            "template": "",
            "alias": "",
            "replace": {},
        },
        "846": 846,
        **kwargs,
    }
    return kwargs
