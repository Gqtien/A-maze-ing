import math
from utils.geometry import Rect
from display.constants import Color, Sprites


def draw_vertical_line(
    y0: int,
    y1: int,
    x: int,
    height: int,
    argb: bytes,
    buffer: memoryview,
    line_size: int
) -> None:
    """Draw a vertical line at x from y0 to y1."""
    # Skip out-of-bounds pixels
    y0 = max(0, y0)
    y1 = min(y1, height - 1)

    for y in range(y0, y1):
        offset = y * line_size + x * 4
        buffer[offset:offset + 4] = argb

def draw_rect(rect: Rect, argb: bytes, buffer: memoryview, line_size: int) -> None:
    """Draw a filled rectangle with a color."""
    for dx in range(rect.width):
        for dy in range(rect.height):
            put_pixel(rect.x + dx, rect.y + dy, argb, buffer, line_size)


def put_pixel(x: int, y: int, argb: bytes, buffer: memoryview, line_size: int) -> None:
    """Set one pixel in a buffer."""
    offset: int = y * line_size + x * 4

    # Skip out-of-bounds pixels
    if offset >= buffer.nbytes - 4:
        return

    buffer[offset:offset + 4] = argb


def render_player_sprite(
    camera_pos: tuple[float, float],
    camera_dir: tuple[float, float],
    cell_size: int,
    buffer: memoryview,
    line_size: int
) -> None:
    """Draw the player sprite on the minimap."""
    sprite = Sprites.PLAYER.value
    sprite_width = len(sprite[0]) if sprite else 0
    sprite_height = len(sprite)

    player_pixel_x = int(camera_pos[0] * cell_size)
    player_pixel_y = int(camera_pos[1] * cell_size)

    direction_angle = math.atan2(camera_dir[1], camera_dir[0])
    angle = direction_angle + math.pi / 2
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    center_x = sprite_width / 2.0
    center_y = sprite_height / 2.0

    for sprite_y, row in enumerate(sprite):
        for sprite_x, char in enumerate(row):
            if char == 'P':
                dx = sprite_x - center_x
                dy = sprite_y - center_y

                rotated_x = dx * cos_a - dy * sin_a
                rotated_y = dx * sin_a + dy * cos_a

                pixel_x = int(player_pixel_x + rotated_x)
                pixel_y = int(player_pixel_y + rotated_y)

                put_pixel(
                    pixel_x,
                    pixel_y,
                    Color.PLAYER.value,
                    buffer,
                    line_size
                )
