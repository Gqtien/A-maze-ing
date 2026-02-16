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
    PLAYER = b'\xFF\x00\xFF\xFF'


class Sprites(Enum):
    """Sprite definitions."""

    PLAYER = [
        ".....P.....",
        "....PPP....",
        "...PPPPP...",
        "..PPPPPPP..",
        ".PPPPPPPPP.",
        "PPPPPPPPPPP",
        "PPPPPPPPPPP",
        "PPPPPPPPPPP",
        "PPPPP.PPPPP",
        "PPPP...PPPP",
        "PP.......PP",
    ]
