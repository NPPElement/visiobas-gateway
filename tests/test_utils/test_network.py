import pytest
from visiobas_gateway.utils.network import ping


@pytest.mark.parametrize(
    "host, expected",
    [
        ("localhost", True),
        # ("192.168.1.105", True),
        ("google.com", True),
        ("10.21.10.66", False),
        ("10.21.10.21", False),
    ],
)
async def test_check_ping(host, expected):
    assert await ping(host=host, attempts=1) == expected
