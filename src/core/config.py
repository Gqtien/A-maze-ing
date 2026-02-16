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
    MODE = str


def env_int(name: str, default: str) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return int(default)


class Extremum(Enum):
    WIDTH = 1000
    HEIGHT = 1000
    WIN_W = env_int("SCREEN_WIDTH", "1920")
    WIN_H = env_int("SCREEN_HEIGHT", "1080")
    FOV = 180


def cast_value(value: str, type: type) -> Any:
    try:
        if type is int:
            return int(value)
        elif type is bool:
            v = value.lower()
            if v == "true":
                return True
            if v == "false":
                return False
            raise ValueError(f"Invalid boolean: "
                             f"(expected 'true' or 'false', got {value!r})")
        elif type is str:
            return value
        elif type is tuple:
            parts = [p.strip() for p in value.strip("()").split(",")]
            if len(parts) != 2:
                raise ValueError(
                    f"Expected exactly 2 comma-separated integers, "
                    f"got {len(parts)}"
                )
            return tuple(map(int, parts))
        else:
            raise TypeError(f"Unsupported type: {type}")
    except ValueError:
        raise ValueError(f"Invalid value for type {type}: {value!r}")


def validate_bounds(config: Dict[str, Any]) -> None:
    if not all(key in config for key in ("WIDTH", "HEIGHT", "ENTRY", "EXIT")):
        return

    width = config.get("WIDTH")
    height = config.get("HEIGHT")

    for key in ("ENTRY", "EXIT"):
        if key not in config:
            continue

        x, y = config[key]

        if not (0 <= x < width):
            raise ValueError(
                f"{key} 'x' out of bounds: map width: {width!r}, got {x!r}"
            )

        if not (0 <= y < height):
            raise ValueError(
                f"{key} 'y' out of bounds: map height: {height!r}, got {y!r}"
            )


def validate_mode(config: Dict[str, Any]) -> None:
    if "MODE" not in config:
        return

    mode = config.get("MODE")
    if len(mode) != 4:
        raise ValueError(f"Invalid mode: must be 4 characters, got {mode!r}")


def parse_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")
    if os.path.isdir(path):
        raise IsADirectoryError(f"Config path is a directory, "
                                f"not a file: {path}")

    config: Dict[str, Any] = {}

    try:
        f = open(path, "r", encoding="utf-8")
    except PermissionError:
        raise PermissionError(f"Cannot read config file "
                              f"(permission denied): {path}")
    except OSError as e:
        raise OSError(f"Cannot open config file: {path}") from e

    try:
        with f as file:
            for line in file:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    raise ValueError(f"Invalid config line: {line!r}")
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()

                if key not in ConfigKey.__members__:
                    raise ValueError(f"Unknown config parameter: {key!r}")

                expected_type = ConfigKey[key].value
                try:
                    casted_value = cast_value(value, expected_type)
                except ValueError as e:
                    raise ValueError(
                        f"Invalid value for {key!r}: "
                        f"expected {expected_type.__name__}, got {value!r}"
                    ) from e

                if key in Extremum.__members__:
                    max_val = Extremum[key].value
                    if casted_value > max_val:
                        raise ValueError(
                            f"Value too high for {key!r}: "
                            f"max {max_val}, got {value!r}"
                        )
                    if key in ("WIDTH", "HEIGHT") and casted_value < 1:
                        raise ValueError(
                            f"Value too low for {key!r}: must be >= 1, "
                            f"got {value!r}"
                        )
                    if key in ("WIN_W", "WIN_H", "FOV") and casted_value < 1:
                        raise ValueError(
                            f"Value too low for {key!r}: must be >= 1, "
                            f"got {value!r}"
                        )

                config[key] = casted_value
                validate_bounds(config)
                validate_mode(config)
    except UnicodeDecodeError as e:
        raise ValueError(
            f"Config file is not valid UTF-8: {path}"
        ) from e

    return config
