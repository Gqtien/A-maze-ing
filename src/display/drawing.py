import math
import numpy
from utils.geometry import Rect
from display.constants import Color, Sprites


def draw_horizontal_line(
    y0: int,
    y1: int,
    x: int,
    height: int,
    argb: bytes,
    numpy_buffer: numpy.ndarray,
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


def render_player_sprite(
    camera_pos: tuple[float, float],
    camera_dir: tuple[float, float],
    cell_size: int,
    buffer: memoryview,
    line_size: int,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Draw the player sprite on the minimap."""
    sprite = Sprites.PLAYER.value
    sprite_width = len(sprite[0]) if sprite else 0
    sprite_height = len(sprite)
    if not sprite or sprite_width == 0:
        return

    player_pixel_x = int(camera_pos[0] * cell_size) + offset_x
    player_pixel_y = int(camera_pos[1] * cell_size) + offset_y

    angle = math.atan2(camera_dir[1], camera_dir[0]) + math.pi / 2
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    center_x = (sprite_width - 1) / 2.0
    center_y = (sprite_height - 1) / 2.0

    half = max(sprite_width, sprite_height) + 1
    for dest_y in range(-half, half + 1):
        for dest_x in range(-half, half + 1):
            sx = center_x + dest_x * cos_a + dest_y * sin_a
            sy = center_y - dest_x * sin_a + dest_y * cos_a
            ix, iy = int(sx), int(sy)
            if 0 <= ix < sprite_width and 0 <= iy < sprite_height:
                if sprite[iy][ix] == "P":
                    put_pixel(
                        player_pixel_x + dest_x,
                        player_pixel_y + dest_y,
                        Color.PLAYER.value,
                        buffer,
                        line_size,
                    )
