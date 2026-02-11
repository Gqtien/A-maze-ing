import math
from dataclasses import dataclass
from typing import Any
from libs.mlx.mlx import Mlx
from core.mazegen import Maze


class Vec2:
    """Vector 2d."""

    def __init__(self, x: float, y: float) -> None:
        """Init."""
        self.x: float = x
        self.y: float = y

    def __eq__(self, other: object) -> bool:
        """Equal."""
        if not isinstance(other, Vec2):
            raise NotImplementedError(
                f"Cannot compare Vec2 with {type(other).__name__}"
            )
        return self.x == other.x and self.y == other.y

    def __str__(self) -> str:
        """Str."""
        return f"({self.x:.2f}, {self.y:.2f})"

    def length(self) -> float:
        """Get length."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self) -> None:
        """Make lenght 1."""
        length = self.length()
        if length < 1e-6:
            return
        self.x /= length
        self.y /= length

    def rotate(self, radians: float) -> None:
        """Rotate by given degrees."""
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)

        tmp_x: float = self.x

        self.x = self.x * cos_a - self.y * sin_a
        self.y = tmp_x * sin_a + self.y * cos_a
        self.normalize()


@dataclass
class Rect:
    """Rectangle."""

    x: int
    y: int
    width: int
    height: int


class Camera:
    """Camera."""

    def __init__(self, pos: Vec2, direction: Vec2, FOV: int) -> None:
        """Init cam."""
        self.pos: Vec2 = pos
        self.direction: Vec2 = direction
        self.FOV: int = FOV
        self.fov_scale = math.tan(math.radians(self.FOV) / 2)

        self.speed: float = 0.1  # block/frame

    def move(self, keys: set[int]) -> None:
        """Move the camera."""
        # TODO: collisions
        if 65363 in keys:  # right arrow
            self.direction.rotate(0.08726646)
        elif 65361 in keys:  # left arrow
            self.direction.rotate(-0.08726646)

        if 65364 in keys:  # down arrow
            self.pos.x -= self.direction.x * self.speed
            self.pos.y -= self.direction.y * self.speed
        elif 65362 in keys:  # up arrow
            self.pos.x += self.direction.x * self.speed
            self.pos.y += self.direction.y * self.speed


class Renderer:
    """Wrap mlx."""

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        entry: tuple[int, int],
        exit: tuple[int, int],
        FOV: int,
        maze: Maze,
    ) -> None:
        """Init the mlx, hook functions."""
        self.width: int = width
        self.height: int = height
        self.title: str = title
        self.maze: Maze = maze
        self.keys: set[int] = set()
        self.camera: Camera = Camera(  # TODO: choose pos and dir dynamicly
            pos=Vec2(1.5, 1.5),
            direction=Vec2(1, 0),
            FOV=FOV,
        )

        # mlx
        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.win_ptr = self.mlx.mlx_new_window(
            self.mlx_ptr, width, height, title
        )

        # a/b buffers for buffer swapping
        self.img_ptr_a = self.mlx.mlx_new_image(self.mlx_ptr, width, height)
        self.img_ptr_b = self.mlx.mlx_new_image(self.mlx_ptr, width, height)
        self.buffer_a, self.bits_per_pixel, self.line_size, _endian = (
            self.mlx.mlx_get_data_addr(self.img_ptr_a)
        )
        self.buffer_b, self.bits_per_pixel, self.line_size, _endian = (
            self.mlx.mlx_get_data_addr(self.img_ptr_b)
        )

        self.mlx.mlx_loop_hook(self.mlx_ptr, self.loop, param=None)

        # key hooks
        self.mlx.mlx_hook(self.win_ptr, 2, 1, self.key_down_hook, param=None)
        self.mlx.mlx_hook(self.win_ptr, 3, 2, self.key_up_hook, param=None)

        # precomputed values
        self.half_buffer_size: int = self.buffer_b.nbytes // 2
        floor_color: bytes = b'\x67\x67\x67\xFF'  # BGRA, litte endian
        sky_color: bytes = b'\xEB\xCE\x87\xFF'
        self.blue: bytes = b'\xFF\x00\x00\xFF'
        self.red: bytes = b'\x00\x00\xFF\xFF'
        repeats = self.half_buffer_size // len(floor_color)
        self.sky: bytes = sky_color * repeats
        self.floor: bytes = floor_color * repeats

        self.grid: list[list[bool]] = self.maze.to_grid()

    def render(self) -> None:
        """Render."""
        # sky and floor, precomputed !
        self.buffer_b[:self.half_buffer_size] = self.sky
        self.buffer_b[self.half_buffer_size:] = self.floor

        # raytracing
        for x in range(0, self.width):
            perp_wall_dist, is_vertical = self.cast_ray(x)
            line_height: int = int(self.height // perp_wall_dist)
            line_y: int = self.height // 2 - line_height // 2
            self.draw_vertical_line(
                y0=line_y,
                y1=line_y + line_height,
                x=x,
                argb=self.blue if is_vertical else self.red
            )

        # mlx stuff
        self.mlx.mlx_put_image_to_window(
            self.mlx_ptr, self.win_ptr, self.img_ptr_a, 0, 0
        )

        # swap draw buffers
        self.img_ptr_a, self.img_ptr_b = self.img_ptr_b, self.img_ptr_a
        self.buffer_a, self.buffer_b = self.buffer_b, self.buffer_a

    def cast_ray(self, x: int) -> tuple[float, bool]:
        """Get the distance from a wall in a dir."""
        # FOV stuff and camera plane
        plane_x = -self.camera.direction.y
        plane_y = self.camera.direction.x
        # TODO: move out, precompute
        plane_x *= self.camera.fov_scale
        plane_y *= self.camera.fov_scale

        camera_x: float = 2 * x / self.width - 1  # x in [-1; 1]

        # TODO: scalar ?
        # ray_dir_x = dir.x + plane_x * camera_x
        # ray_dir_y = dir.y + plane_y * camera_x

        ray_dir_x: float = self.camera.direction.x
        ray_dir_y: float = self.camera.direction.y
        ray_dir_x += plane_x * camera_x
        ray_dir_y += plane_y * camera_x

        dx: float = abs(1 / ray_dir_x) if abs(ray_dir_x) > 0.01 else 1e30
        dy: float = abs(1 / ray_dir_y) if abs(ray_dir_y) > 0.01 else 1e30

        map_x: int = int(self.camera.pos.x)
        map_y: int = int(self.camera.pos.y)

        # init step_x (for map indexes) and dist_x
        step_x: int = 0
        step_y: int = 0
        dist_x: float = 0.0
        dist_y: float = 0.0
        if ray_dir_x > 0:
            step_x = 1
            dist_x = (map_x + 1.0 - self.camera.pos.x) * dx
        else:
            step_x = -1
            dist_x = (self.camera.pos.x - map_x) * dx
        if ray_dir_y > 0:
            step_y = 1
            dist_y = (map_y + 1.0 - self.camera.pos.y) * dy
        else:
            step_y = -1
            dist_y = (self.camera.pos.y - map_y) * dy

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

            if map_x < 0 or map_y < 0:
                break
            if map_x >= len(self.grid[0]) - 1 or map_y >= len(self.grid) - 1:
                break
            hit = self.grid[map_y][map_x]

        perp_wall_dist: float = 0.0
        if is_vertical:
            perp_wall_dist = dist_x - dx
        else:
            perp_wall_dist = dist_y - dy

        return perp_wall_dist, is_vertical

    def run(self) -> None:
        """Start infinite loop."""
        self.mlx.mlx_loop(self.mlx_ptr)
        self.mlx.mlx_loop_exit(self.mlx_ptr)

    def loop(self, _: Any) -> None:
        """Loop."""
        self.render()
        self.camera.move(self.keys)

    def clear(self) -> None:
        """Clear the memory buffer."""
        self.buffer_b[:] = b"\x00" * self.buffer_b.nbytes

    def draw_vertical_line(
            self, y0: int, y1: int, x: int, argb: bytes
    ) -> None:
        """Draw a vertical line."""
        # Skip out-of-bounds pixels
        y0 = max(0, y0)
        y1 = min(y1, self.height - 1)

        for y in range(y0, y1):
            offset = y * self.line_size + x * 4
            self.buffer_b[offset:offset + 4] = argb

    def draw_rect(self, rect: Rect, argb: int) -> None:
        """Draw a rect."""
        for dx in range(rect.width):
            for dy in range(rect.height):
                self.put_pixel(rect.x + dx, rect.y + dy, argb)

    def put_pixel(self, x: int, y: int, argb: int) -> None:
        """Put a pixel."""
        # Skip out-of-bounds pixels
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        offset = y * self.line_size + x * 4
        self.buffer_b[offset:offset + 4] = argb.to_bytes(4, 'little')

    def key_down_hook(self, key: int, _param: None) -> None:
        """Add keys to self.keys."""
        match key:
            case 65307:  # ESC
                self.mlx.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
                self.mlx.mlx_destroy_image(self.mlx_ptr, self.img_ptr_a)
                self.mlx.mlx_destroy_image(self.mlx_ptr, self.img_ptr_b)
                self.mlx.mlx_loop_exit(self.mlx_ptr)
                return
            # case _:
            #     print(f"Pressed key: {key}")
        self.keys.add(key)

    def key_up_hook(self, key: int, _param: None) -> None:
        """Remove keys from self.keys."""
        self.keys.discard(key)


def run_mlx_3d(maze: Maze, settings: dict[str, Any]) -> None:
    """Run the 3d rendering."""
    print(settings)
    renderer = Renderer(
        settings["WIN_W"],
        settings["WIN_H"],
        settings["WIN_TITLE"],
        settings["ENTRY"],
        settings["EXIT"],
        settings["FOV"],
        maze
    )
    renderer.run()
