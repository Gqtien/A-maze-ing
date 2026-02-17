from functools import lru_cache
from display.constants import Color


def cast_ray(
    x: int,
    width: int,
    camera_pos: tuple[float, float],
    camera_dir: tuple[float, float],
    fov_scale: float,
    grid: list[list[bool]],
    grid_width: int,
    grid_height: int,
    entry_pos: tuple[int, int],
    exit_pos: tuple[int, int],
) -> tuple[float, bytes]:
    """Get the distance from a wall in a direction."""
    # FOV stuff and camera plane
    plane_x = -camera_dir[1] * fov_scale
    plane_y = camera_dir[0] * fov_scale

    camera_x: float = 2 * x / width - 1  # x in [-1; 1]

    ray_dir_x: float = camera_dir[0] + plane_x * camera_x
    ray_dir_y: float = camera_dir[1] + plane_y * camera_x

    dx: float = abs(1 / ray_dir_x) if abs(ray_dir_x) > 0.01 else 1e30
    dy: float = abs(1 / ray_dir_y) if abs(ray_dir_y) > 0.01 else 1e30

    map_x: int = int(camera_pos[0])
    map_y: int = int(camera_pos[1])

    # init step_x (for map indexes) and dist_x
    step_x: int = 0
    step_y: int = 0
    dist_x: float = 0.0
    dist_y: float = 0.0
    if ray_dir_x > 0:
        step_x = 1
        dist_x = (map_x + 1.0 - camera_pos[0]) * dx
    else:
        step_x = -1
        dist_x = (camera_pos[0] - map_x) * dx
    if ray_dir_y > 0:
        step_y = 1
        dist_y = (map_y + 1.0 - camera_pos[1]) * dy
    else:
        step_y = -1
        dist_y = (camera_pos[1] - map_y) * dy

    # DDA algo loop
    hit: bool = False
    while not hit:
        if dist_x < dist_y:
            dist_x += dx
            map_x += step_x
            is_vertical = True
        else:
            dist_y += dy
            map_y += step_y
            is_vertical = False

        # clamp map indexes
        if (
                map_x < 0
                or map_y < 0
                or map_x >= grid_width
                or map_y >= grid_height
        ):
            break
        hit = grid[map_y][map_x]

    # get wall color
    perp_wall_dist: float = dist_x - dx if is_vertical else dist_y - dy
    color: bytes = darken_color_to_bytes(Color.WALL, not is_vertical)
    if is_vertical:
        map_x -= step_x
    else:
        map_y -= step_y
    if (map_x, map_y) == entry_pos:
        color = darken_color_to_bytes(Color.GREEN, not is_vertical)
    elif (map_x, map_y) == exit_pos:
        color = darken_color_to_bytes(Color.RED, not is_vertical)

    return perp_wall_dist, color


@lru_cache()  # NOTE: that's one of the biggest opti, dont remove !
def darken_color_to_bytes(
    color: Color, do_darken: bool = True, amount: int = 0x20
) -> bytes:
    """Subtract amount (default 0x20) from color, excluding alpha."""
    if not do_darken:
        return color.value
    return bytes(
        map(lambda byte: max(0x0, byte - amount), color.value[:3])
    ) + color.value[3:]
