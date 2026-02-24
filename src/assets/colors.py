from enum import Enum


class Color(Enum):
    """Colors in hex BGRA format."""

    RED = b'\x00\x00\xFF\xFF'
    GREEN = b'\x00\xFF\x00\xFF'
    BLUE = b'\xFF\x00\x00\xFF'
    WHITE = b'\x00\x00\x00\xFF'
    BLACK = b'\xFF\xFF\xFF\xFF'
    FLOOR = b'\x37\x37\x37\xFF'
    SKY = b'\xEB\xCE\x87\xFF'
    WALL = b'\xA0\xA0\xA0\xFF'
    PLAYER = b'\x9C\x5D\x3A\xFF'
    PATTERN = b'\xFF\x00\x00\xFF'


class ColorPalette(Enum):
    """Color palette for minimap."""

    MAGENTA = b"\xD8\xA8\xD8\xFF"
    WHITE = b"\xFF\xFF\xFF\xFF"
    CYAN = b"\xD8\xD8\xA8\xFF"
    BLUE = b"\xD8\xA8\xA8\xFF"
    RED = b"\xA8\xA8\xD8\xFF"
    GREEN = b"\xA8\xD8\xA8\xFF"
    YELLOW = b"\xA8\xD8\xD8\xFF"
