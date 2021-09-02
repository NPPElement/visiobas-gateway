from gateway.verifier import _round
import pytest


@pytest.mark.parametrize(
    "before, resolution, after",
    [
        (1.23456789, 0.1, 1.2),
        (1.23456789, 0.05, 1.25),
        (1.23456789, 1, 1),
        (1.23456789, 5, 0),
        (-1.23456789, 0.25, -1.25)
    ]
)
def test__round_happy(before, resolution, after):
    assert _round(before, resolution) == after


@pytest.mark.parametrize(
    "resolution",
    [
        None,
        0,
        -1,
        -0.5,
        "bad_resolution",
    ]
)
def test__round_bad_resolution(resolution):
    with pytest.raises(ValueError):
        _round(1.23456789, resolution)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "1.23456789",
        "bad_value",
        float("inf")
    ]
)
def test__round_bad_value(value):
    with pytest.raises(ValueError):
        _round(value, 0.1)


class TestVerifier:
    pass
