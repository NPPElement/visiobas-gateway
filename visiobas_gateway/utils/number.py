from __future__ import annotations
_FLOAT_FORMAT = ".10f"


def round_with_resolution(value: float | int, resolution: int | float) -> float:
    if not isinstance(resolution, (int, float)):
        raise ValueError("`resolution` must be number.")
    if resolution <= 0:
        raise ValueError("`resolution` must be greater than 0.")

    if not isinstance(value, (int, float)):
        raise ValueError("`value` must be number.")
    if value in {float("-inf"), float("inf")}:
        raise ValueError("`value` must not be infinity.")

    rounded = round(float(value) / resolution) * resolution
    if isinstance(resolution, int):
        return rounded

    _, fractional_part = format(resolution, _FLOAT_FORMAT).split(".", maxsplit=1)
    digits = len(fractional_part)
    return round(rounded, ndigits=digits)
