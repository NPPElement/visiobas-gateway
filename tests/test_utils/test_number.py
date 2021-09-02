from gateway.utils import round_with_resolution
import pytest


@pytest.mark.parametrize(
    "before, resolution, after",
    [
        (1.23456789, 0.1, 1.2),
        (1.23456789, 0.05, 1.25),
        (1.23456789, 1, 1),
        (1.23456789, 5, 0),
        (-1.23456789, 0.25, -1.25),
    ],
)
def test_round_with_resolution_happy(before, resolution, after):
    assert round_with_resolution(before, resolution) == after


@pytest.mark.parametrize(
    "resolution",
    [
        None,
        0,
        -1,
        -0.5,
        "bad_resolution",
    ],
)
def test_round_with_resolution_bad_resolution(resolution):
    with pytest.raises(ValueError):
        round_with_resolution(1.23456789, resolution)


@pytest.mark.parametrize("value", [None, "1.23456789", "bad_value", float("inf")])
def test_round_with_resolution_bad_value(value):
    with pytest.raises(ValueError):
        round_with_resolution(value, 0.1)
