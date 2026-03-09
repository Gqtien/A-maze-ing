import os
from enum import Enum, auto
from typing import Any, NamedTuple
from assets import ColorPalette


class Algo(Enum):
    """Maze generation alogithm."""

    PRIM = auto()
    BACKTRACKING = auto()


class Mode:
    """Key layout."""

    _member_names_: list[str] = ["4 chars"]

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
            raise ValueError(
                f"'MODE' must be exactly 4 characters "
                f"(forward,left,back,right), got {len(raw)} "
                f"character{'' if len(raw) == 1 else 's'} in {value!r}"
            )
        if not all(c.isalpha() for c in raw):
            raise ValueError(
                f"'MODE' must be 4 letters only "
                f"(no digits, spaces or symbols), got {value!r}"
            )
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
    """Two-digit pattern."""

    _member_names_: list[str] = ["2 digits"]

    class PatternDigits(NamedTuple):
        """Names of the two Digits enum members for patterns."""

        first: str
        second: str

    def __init__(self, value: str) -> None:
        """Parse value: exactly 2 digits."""
        raw = value.strip()
        if len(raw) != 2:
            raise ValueError(
                f"'PATTERN' must be exactly 2 digits, got {value!r}"
            )
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
            raise ValueError(f"'PATTERN' digits must be 0-9, got {value!r}")
        self._digits = Pattern.PatternDigits(numbers[first], numbers[second])

    def digits(self) -> "Pattern.PatternDigits":
        """Return the two digit names for this pattern."""
        return self._digits


class MandatoryConfigKey(Enum):
    """MandatoryConfigKey."""

    WIDTH = int
    HEIGHT = int
    ENTRY = tuple
    EXIT = tuple
    OUTPUT_FILE = str
    PERFECT = bool


class OptionalConfigKey(Enum):
    """OptionalConfigKey."""

    SEED = int
    WIN_W = int
    WIN_H = int
    WIN_TITLE = str
    FOV = int
    ALGO = Algo
    SOLUTION = bool
    MODE = Mode
    COLOR = ColorPalette
    PATTERN = Pattern
    FPS = bool
    MOUSE = bool
    PLAYBACK_SPEED = float


def env_int(name: str, default: str) -> int:
    """Safely get int from env."""
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return int(default)


class Extremum(Enum):
    """Config max value."""

    WIDTH = 1000
    HEIGHT = 1000
    WIN_W = env_int("SCREEN_WIDTH", "1920")
    WIN_H = env_int("SCREEN_HEIGHT", "1080")
    FOV = 120


def cast_value(value: str, target: type) -> Any:
    """Cast value to type."""

    if target in (int, float, str):
        return target(value)
    elif target is bool:
        if (v := value.lower()) not in ("true", "false"):
            raise ValueError(f"Invalid boolean: "
                             f"(expected 'true' or 'false', got {value!r})")
            return v == "true"
    elif target is tuple:
        parts = [p.strip() for p in value.strip("()").split(",")]
        if len(parts) != 2:
            raise ValueError(
                f"Expected exactly 2 comma-separated integers, "
                f"got {len(parts)}"
            )
        return tuple(map(int, parts))
    elif target in (Algo, ColorPalette):
        return target[value.strip().upper()]
    elif target in (Pattern, Mode):
        return target(value.strip())
    else:
        raise TypeError(f"Unsupported type: {target}")


def validate_bounds(config: dict[str, Any]) -> None:
    """Validate that entry and exit pos are in maze."""
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


def parse_config(path: str) -> dict[str, Any]:
    """Parse the config file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    if os.path.isdir(path):
        raise IsADirectoryError(f"Config path is a directory, "
                                f"not a file: {path}")

    config: dict[str, Any] = {}

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

                if (
                    key not in MandatoryConfigKey.__members__ and
                    key not in OptionalConfigKey.__members__
                ):
                    raise ValueError(f"Unknown config parameter: {key!r}")

                if key in MandatoryConfigKey.__members__:
                    expected_type = MandatoryConfigKey[key].value
                else:
                    expected_type = OptionalConfigKey[key].value

                try:
                    casted_value = cast_value(value, expected_type)
                except ValueError as e:
                    msg = f"Invalid value for {key!r}: "
                    if hasattr(expected_type, "_member_names_"):
                        opts = ', '.join(expected_type._member_names_).lower()
                        msg += f"expected {expected_type.__name__} "
                        msg += f"({opts}), got {value!r}"
                        raise ValueError(msg) from e
                    else:
                        msg += f"expected {expected_type.__name__}, "
                        msg += f"got {value!r}"
                        raise ValueError(msg) from e

                if key in Extremum.__members__:
                    max_val = Extremum[key].value
                    if casted_value > max_val:
                        raise ValueError(
                            f"Value too high for {key!r}: "
                            f"max {max_val}, got {value!r}"
                        )
                if key in (
                    "WIDTH",
                    "HEIGHT",
                    "WIN_W",
                    "WIN_H",
                    "PLAYBACK_SPEED"
                ) and casted_value < 1:
                    raise ValueError(
                        f"Value too low for {key!r}: must be >= 1, "
                        f"got {value!r}"
                    )

                if key in ("WIN_W", "WIN_H") and casted_value < 4:
                    raise ValueError(
                        f"Value too low for {key!r}: must be >= 4 "
                        f"(minimap needs non-zero size), got {value!r}"
                    )

                config[key] = casted_value
            validate_bounds(config)

            missing_keys = [
                key for key in MandatoryConfigKey.__members__
                if key not in config or config[key] is None
            ]

            if missing_keys:
                raise ValueError(
                    "Missing mandatory config parameter"
                    f"{'s' if len(missing_keys) > 1 else ''}: "
                    f"{', '.join(missing_keys)}"
                )
    except PermissionError:
        raise PermissionError(
            f"Cannot read config file (permission denied): {path}"
        )
    except OSError as e:
        raise OSError(f"Cannot read config file: {path}") from e
    except UnicodeDecodeError as e:
        raise ValueError(
            f"Config file is not valid UTF-8: {path}"
        ) from e

    return config
