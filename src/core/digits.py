from enum import Enum

class Digits(Enum):
    """Digits."""

    ZERO = [
        ".OOO.",
        "O...O",
        "O...O",
        "O...O",
        "O...O",
        ".OOO.",
    ]

    ONE = [
        "...O.",
        "..OO.",
        "O..O.",
        "...O.",
        "...O.",
        "OOOOO",
    ]

    TWO = [
        ".OOO.",
        "O...O",
        "...O.",
        "..O..",
        ".O...",
        "OOOOO",
    ]

    THREE = [
        "OOOOO",
        "....O",
        "..OO.",
        "....O",
        "O...O",
        ".OOO.",
    ]

    FOUR = [
        "O...O",
        "O...O",
        "OOOOO",
        "....O",
        "....O",
        "....O",
    ]

    FIVE = [
        "OOOOO",
        "O....",
        "OOOO.",
        "....O",
        "O...O",
        ".OOO.",
    ]

    SIX = [
        ".OOO.",
        "O....",
        "OOOO.",
        "O...O",
        "O...O",
        ".OOO.",
    ]

    SEVEN = [
        "OOOOO",
        "....O",
        "...O.",
        "..O..",
        ".O...",
        "O....",
    ]

    EIGHT = [
        ".OOO.",
        "O...O",
        ".OOO.",
        "O...O",
        "O...O",
        ".OOO.",
    ]

    NINE = [
        ".OOO.",
        "O...O",
        "O...O",
        ".OOOO",
        "....O",
        ".OOO.",
    ]

    TWO_SMALL = [
        "OOO",
        "..O",
        "OOO",
        "O..",
        "OOO",
    ]

    FOUR_SMALL = [
        "O.O",
        "O.O",
        "OOO",
        "..O",
        "..O",
    ]
