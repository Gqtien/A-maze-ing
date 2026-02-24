import math
from functools import lru_cache
import numpy
import numpy.typing as npt
from utils import Rect
from assets import (
    CHARS,
    CHAR_GLYPH_H,
    CHAR_GLYPH_W,
    SPRITES,
    SPRITE_H,
    SPRITE_W,
)


def draw_horizontal_line(
    y0: int,
    y1: int,
    x: int,
    height: int,
    argb: bytes,
    numpy_buffer: npt.NDArray[numpy.uint8],
) -> None:
    """Draw a vertical line at x from y0 to y1."""
    y0 = max(0, y0)
    y1 = min(y1, height - 1)

    if y0 > y1:
        return

    color_array = numpy.frombuffer(argb, dtype=numpy.uint8)
    numpy_buffer[y0:y1, x, :] = color_array


def draw_rect(
    rect: Rect,
    argb: bytes,
    buffer: memoryview,
    line_size: int,
) -> None:
    """Draw a filled rectangle with a color."""
    for dx in range(rect.width):
        for dy in range(rect.height):
            put_pixel(rect.x + dx, rect.y + dy, argb, buffer, line_size)


def put_pixel(
    x: int,
    y: int,
    argb: bytes,
    buffer: memoryview,
    line_size: int,
) -> None:
    """Set one pixel in a buffer."""
    # Skip out-of-bounds pixels
    if x < 0 or y < 0:
        return

    width_px: int = line_size // 4
    height_px: int = buffer.nbytes // line_size

    if x >= width_px or y >= height_px:
        return

    offset: int = y * line_size + x * 4
    buffer[offset:offset + 4] = argb


@lru_cache(maxsize=None)  # NOTE: don't remove
def alpha_for_char(char: str) -> npt.NDArray[numpy.float32]:
    """Alpha bitmap for one char. Cached."""
    if len(char) != 1:
        return numpy.zeros((CHAR_GLYPH_H, CHAR_GLYPH_W), dtype=numpy.float32)

    glyph = CHARS.get(char)
    if not glyph:
        return numpy.zeros((CHAR_GLYPH_H, CHAR_GLYPH_W), dtype=numpy.float32)

    # build opacty grid
    a: npt.NDArray[numpy.float32] = numpy.zeros(
        (CHAR_GLYPH_H, CHAR_GLYPH_W),
        dtype=numpy.float32
    )
    for row, line in enumerate(glyph):
        for col, cell in enumerate(line):
            if "0" <= cell <= "9":
                a[row, col] = (int(cell) + 1) / 10.0
    return a


def put_string(
    string: str,
    x: int,
    y: int,
    argb: bytes,
    numpy_buffer: npt.NDArray[numpy.uint8],
) -> None:
    """Draw a string."""
    if not string:
        return

    # build alpha mask for the whole string
    alpha = numpy.hstack([alpha_for_char(char) for char in string])
    height, width = alpha.shape

    # clip to buffer bounds
    y1 = min(y + height, numpy_buffer.shape[0])
    x1 = min(x + width, numpy_buffer.shape[1])
    if y >= y1 or x >= x1:
        return

    # region of the buffer where we draw the text
    text_region = numpy_buffer[y:y1, x:x1, :]
    alpha_region = alpha[:y1 - y, :x1 - x, numpy.newaxis]
    # blend text color onto background
    color_array = numpy.frombuffer(argb, dtype=numpy.uint8)
    text_region[:] = (
        text_region * (1.0 - alpha_region)
        + alpha_region * color_array
    )


def draw_player_sprite(
    camera_pos: tuple[float, float],
    camera_dir: tuple[float, float],
    cell_size: int,
    buffer: memoryview,
    line_size: int,
    color: bytes,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Draw the player sprite on the minimap."""
    center_px = (
        round(camera_pos[0] * cell_size) + offset_x,
        round(camera_pos[1] * cell_size) + offset_y,
    )
    angle = math.atan2(camera_dir[1], camera_dir[0]) + math.pi / 2
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    half = max(SPRITE_W, SPRITE_H) + 1
    sprite_cx = (SPRITE_W - 1) / 2.0
    sprite_cy = (SPRITE_H - 1) / 2.0

    for dest_y in range(-half, half + 1):
        for dest_x in range(-half, half + 1):
            sx = sprite_cx + dest_x * cos_a + dest_y * sin_a
            sy = sprite_cy - dest_x * sin_a + dest_y * cos_a
            ix, iy = int(round(sx)), int(round(sy))
            if (
                0 <= ix < SPRITE_W
                and 0 <= iy < SPRITE_H
                and SPRITES["PLAYER"][iy][ix] == "P"
            ):
                put_pixel(
                    center_px[0] + dest_x,
                    center_px[1] + dest_y,
                    color,
                    buffer,
                    line_size,
                )
