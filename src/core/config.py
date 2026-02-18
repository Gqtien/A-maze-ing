import os
from enum import Enum
from typing import Any, Dict, NamedTuple


class Mode:
    """Key layout"""

    class KeyBindings(NamedTuple):
        """Keys for forward, left, back, right."""
        forward: str
        left: str
        back: str
        right: str

    def __init__(self, value: str) -> None:
        """Parse value: exactly 4 letters for each direction."""
        raw = value.strip()
        if len(raw) != 4:
            print(
                f"MODE must be exactly 4 characters (forward,left,back,right),"
                f" got {len(raw)} character{'' if len(raw) == 1 else 's'} "
                f"in {value!r}"
            )
            exit(1)
        if not all(c.isalpha() for c in raw):
            print(
                f"MODE must be 4 letters only (no digits, spaces or symbols), "
                f"got {value!r}"
            )
            exit(1)
        keys = [raw[0], raw[1], raw[2], raw[3]]
        self.bindings = Mode.KeyBindings(
            forward=keys[0],
            left=keys[1],
            back=keys[2],
            right=keys[3],
        )

    def keys(self) -> "Mode.KeyBindings":
        """Return key bindings for this mode."""
        return self.bindings


class Pattern:
    """Two-digit pattern"""
    class PatternDigits(NamedTuple):
        """Names of the two Digits enum members for patterns."""
        first: str
        second: str

    def __init__(self, value: str) -> None:
        """Parse value: exactly 2 digits."""
        raw = value.strip()
        if len(raw) != 2:
            print(f"PATTERN must be exactly 2 digits, got {value!r}")
            exit(1)
        numbers = [
            "ZERO", "ONE", "TWO", "THREE", "FOUR",
            "FIVE", "SIX", "SEVEN", "EIGHT", "NINE",
        ]
        try:
            first = int(raw[0])
            second = int(raw[1])
            if first not in range(10) or second not in range(10):
                raise ValueError
        except ValueError:
            print(f"PATTERN digits must be 0-9, got {value!r}")
            exit(1)
        self._digits = Pattern.PatternDigits(numbers[first], numbers[second])

    def digits(self) -> "Pattern.PatternDigits":
        """Return the two digit names for this pattern."""
        return self._digits


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
    MODE = Mode
    PATTERN = Pattern
    FPS = bool


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
    FOV = 120


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
        elif type is Pattern:
            return Pattern(value.strip())
        elif type is Mode:
            return Mode(value.strip())
        else:
            raise TypeError(f"Unsupported type: {type}")
    except (ValueError, KeyError):
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

    if config["ENTRY"] == config["EXIT"]:
        raise ValueError(
            "ENTRY and EXIT must be different "
            f"(both set to {config['ENTRY']!r})"
        )


def parse_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")
    if os.path.isdir(path):
        raise IsADirectoryError(f"Config path is a directory, "
                                f"not a file: {path}")

    config: Dict[str, Any] = {}

    try:
        with open(path, "r", encoding="utf-8") as file:
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
                    type_name = getattr(
                        expected_type, "__name__", repr(expected_type)
                    )
                    raise ValueError(
                        f"Invalid value for {key!r}: "
                        f"expected {type_name}, got {value!r}"
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
    except PermissionError:
        raise PermissionError(
            f"Cannot read config file (permission denied): {path}"
        )
    except OSError as e:
        raise OSError(f"Cannot open config file: {path}") from e
    except UnicodeDecodeError as e:
        raise ValueError(
            f"Config file is not valid UTF-8: {path}"
        ) from e

    return config
