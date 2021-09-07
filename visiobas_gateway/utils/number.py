from typing import Union


def round_with_resolution(value: Union[float, int], resolution: Union[int, float]) -> float:
    if not isinstance(resolution, (int, float)) or resolution <= 0:
        raise ValueError("`resolution` must be number greater than 0")
    if not isinstance(value, (int, float)) or value in {float("-inf"), float("inf")}:
        raise ValueError("`value` must be number")

    rounded = round(float(value) / resolution) * resolution
    if isinstance(resolution, int):
        return rounded
    _, fractional_part = str(resolution).split(".", maxsplit=1)
    digits = len(fractional_part)
    return round(rounded, ndigits=digits)
