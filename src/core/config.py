import os
from enum import Enum
from typing import Any, Dict


class ConfigKey(Enum):
    WIDTH = int
    HEIGHT = int
    ENTRY = tuple
    EXIT = tuple
    PERFECT = bool
    SEED = int
    OUTPUT_FILE = str
    WIN_W = int
    WIN_H = int
    WIN_TITLE = str
    FOV = int


class Extremum(Enum):
    WIN_W = int(os.environ.get("SCREEN_WIDTH", "1920"))
    WIN_H = int(os.environ.get("SCREEN_HEIGHT", "1080"))
    FOV = 180


def cast_value(value: str, type: type) -> Any:
    try:
        if type is int:
            return int(value)
        elif type is bool:
            if value.lower() in "true" or "false":
                return value.lower() == "true"
            pass
        elif type is str:
            return value
        elif type is tuple:
            return tuple(map(int, value.strip("()").split(",")))
        else:
            raise TypeError(f"Unsupported type: {type}")
    except ValueError:
        raise ValueError(f"Invalid value for type {type}: {value}")


def validate_bounds(config: Dict[str, Any]) -> None:
    if not all(key in config for key in ("WIDTH", "HEIGHT", "ENTRY", "EXIT")):
        return

    width = config.get("WIDTH")
    height = config.get("HEIGHT")

    for key in ("ENTRY", "EXIT"):
        if key not in config:
            continue

        x, y = config[key]

        if not (0 <= x < width):  # if width = 25 and point x = 25, gen crash
            raise ValueError(
                f"{key} 'x' out of bounds: {x} (map width: {width})"
            )

        if not (0 <= y < height):  # if height = 25 and point y = 25, gen crash
            raise ValueError(
                f"{key} 'y' out of bounds: {y} (map height: {height})"
            )


def parse_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")

    config: Dict[str, Any] = {}

    with open(path, "r") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            key, value = line.split("=")
            key = key.strip()
            value = value.strip()

            if key not in ConfigKey.__members__:
                raise ValueError(f"Unknown config parameter: {key!r}")

            expected_type = ConfigKey[key].value
            try:
                casted_value = cast_value(value, expected_type)
            except ValueError as e:
                raise ValueError(
                    f"Invalid value for {key!r}"
                    + f"(expected {expected_type.__name__}): {value}"
                ) from e

            if (
                key in Extremum.__members__
                and casted_value > Extremum[key].value
            ):
                raise ValueError(
                    f"Invalid value for {key!r}"
                    + f"(max {Extremum[key].value}): {value}"
                )

            config[key] = casted_value
            validate_bounds(config)

    return config
