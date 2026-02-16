import math
from dataclasses import dataclass


class Vec2:
    """2D vector."""

    def __init__(self, x: float, y: float) -> None:
        """Store x, y."""
        self.x: float = x
        self.y: float = y

    def __eq__(self, other: object) -> bool:
        """Return true if other is a Vec2 with same x and y."""
        if not isinstance(other, Vec2):
            raise NotImplementedError(
                f"Cannot compare Vec2 with {type(other).__name__}"
            )
        return self.x == other.x and self.y == other.y

    def __str__(self) -> str:
        """Format as '(x.xx, y.yy)'."""
        return f"({self.x:.2f}, {self.y:.2f})"

    def length(self) -> float:
        """Euclidean norm."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self) -> None:
        """Make length 1."""
        length = self.length()
        if length < 1e-6:
            return
        self.x /= length
        self.y /= length

    def rotate(self, radians: float) -> None:
        """Rotate in-place by angle in radians (counterclock)."""
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)

        tmp_x: float = self.x

        self.x = self.x * cos_a - self.y * sin_a
        self.y = tmp_x * sin_a + self.y * cos_a
        self.normalize()


@dataclass
class Rect:
    """Rectangle in pixel coordinates (x, y, width, height)."""

    x: int
    y: int
    width: int
    height: int
