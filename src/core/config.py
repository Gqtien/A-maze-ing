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
                    f"Invalid value for {key!r} (expected {expected_type.__name__}): {value}"
                ) from e

            config[key] = casted_value

    return config
