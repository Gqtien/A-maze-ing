import math
from dataclasses import dataclass
from typing import Any
from libs.mlx.mlx import Mlx
from src.core.mazegen import Maze


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

    def copy(self) -> "Vec2":
        """Copy the object."""
        return Vec2(self.x, self.y)

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

    def rotate(self, degrees: float) -> None:
        """Rotate by given degrees."""
        radians = math.radians(degrees)
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)

        tmp_x: float = self.x

        self.x = self.x * cos_a - self.y * sin_a
        self.y = tmp_x * sin_a + self.y * cos_a


@dataclass
class Rect:
    """Rectangle."""

    x: int
    y: int
    width: int
    height: int


@dataclass
class Camera:
    """Camera."""

    pos: Vec2
    dir: Vec2
    FOV: int = 60  # TODO: load it from config

    speed: float = 0.1  # block/frame

    def move(self, keys: set[int]) -> None:
        """Move the camera."""
        if 65363 in keys:  # right arrow
            self.dir.rotate(10)
        elif 65361 in keys:  # left arrow
            self.dir.rotate(-10)

        if 65364 in keys:  # down arrow
            self.pos.x -= self.dir.x * self.speed
            self.pos.y -= self.dir.y * self.speed
        elif 65362 in keys:  # up arrow
            self.pos.x += self.dir.x * self.speed
            self.pos.y += self.dir.y * self.speed


class Renderer:
    """Wrap mlx."""

    def __init__(
        self, width: int, height: int, title: str, maze: Maze
    ) -> None:
        """Init the mlx, hook functions."""
        self.width: int = width
        self.height: int = height
        self.time: str = title

        # mlx
        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.win_ptr = self.mlx.mlx_new_window(
            self.mlx_ptr, width, height, title
        )
        self.img_ptr_a = self.mlx.mlx_new_image(self.mlx_ptr, width, height)
        self.img_ptr_b = self.mlx.mlx_new_image(self.mlx_ptr, width, height)
        self.buffer_a, self.bits_per_pixel, self.line_size, _ = (
            self.mlx.mlx_get_data_addr(self.img_ptr_a)
        )
        self.buffer_b, self.bits_per_pixel, self.line_size, _ = (
            self.mlx.mlx_get_data_addr(self.img_ptr_b)
        )

        self.mlx.mlx_loop_hook(self.mlx_ptr, self.loop, param=None)

        # key hooks
        self.mlx.mlx_hook(self.win_ptr, 2, 1, self.key_down_hook, param=None)
        self.mlx.mlx_hook(self.win_ptr, 3, 2, self.key_up_hook, param=None)

        self.maze: Maze = maze
        self.camera: Camera = Camera(pos=Vec2(1.5, 1.5), dir=Vec2(1, 0))
        self.keys: set[int] = set()

        self.mlx.mlx_do_sync(self.mlx_ptr)

    def render(self) -> None:
        """Render."""
        # sky and floor
        half_size: int = self.buffer_b.nbytes // 2
        floor_color: bytes = b"\x67\x67\x67\xff"  # BGRA, big endian
        sky_color: bytes = b"\xeb\xce\x87\xff"
        repeats = half_size // len(floor_color)
        self.buffer_b[:half_size] = sky_color * repeats
        self.buffer_b[half_size:] = floor_color * repeats

        # raytracing
        line_width: int = 5
        for x in range(0, self.width, line_width):
            perp_wall_dist, side = self.cast_ray(x)
            line_height: int = int(self.height // perp_wall_dist)
            line_y: int = self.height // 2 - line_height // 2
            self.draw_rect(
                Rect(x, line_y, line_width, line_height),
                0xFFFF0000 if side == 1 else 0xFF0000FF,
            )

        # mlx stuff
        self.mlx.mlx_put_image_to_window(
            self.mlx_ptr, self.win_ptr, self.img_ptr_a, 0, 0
        )
        self.mlx.mlx_sync(self.mlx_ptr, 0, self.win_ptr)

        # swap draw buffers
        self.img_ptr_a, self.img_ptr_b = self.img_ptr_b, self.img_ptr_a
        self.buffer_a, self.buffer_b = self.buffer_b, self.buffer_a

    def cast_ray(self, x: int) -> Vec2:
        """Get the distance from a wall in a dir."""
        dist_x: float = self.camera.pos.x
        dist_y: float = self.camera.pos.y

        grid: list[list[bool]] = self.maze.to_grid()

        # TODO: remove
        self.camera.dir.normalize()

        # NOTE: FOV stuff and camera plane
        plane_x = -self.camera.dir.y
        plane_y = self.camera.dir.x
        fov_scale = math.tan(math.radians(self.camera.FOV) / 2)
        plane_x *= fov_scale
        plane_y *= fov_scale

        camera_x: float = 2 * x / self.width - 1  # x in [-1; 1]

        ray_dir: Vec2 = self.camera.dir.copy()
        ray_dir.x += plane_x * camera_x
        ray_dir.y += plane_y * camera_x

        # NOTE: might remove later
        ray_dir.normalize()

        dx: float = abs(1 / ray_dir.x) if abs(ray_dir.x) > 0.01 else 1e30
        dy: float = abs(1 / ray_dir.y) if abs(ray_dir.y) > 0.01 else 1e30

        map_x: int = int(self.camera.pos.x)
        map_y: int = int(self.camera.pos.y)

        # init step_x (for map indexes) and dist_x
        if ray_dir.x > 0:
            step_x: int = 1
            dist_x: float = (map_x + 1.0 - self.camera.pos.x) * dx
        else:
            step_x: int = -1
            dist_x: float = (self.camera.pos.x - map_x) * dx
        if ray_dir.y > 0:
            step_y: int = 1
            dist_y: float = (map_y + 1.0 - self.camera.pos.y) * dy
        else:
            step_y: int = -1
            dist_y: float = (self.camera.pos.y - map_y) * dy

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

            if map_x <= 0 or map_y <= 0:
                break
            if map_x >= self.maze.width - 1 or map_y >= self.maze.height - 1:
                break
            hit = grid[map_y][map_x]

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
        for i in range(4):
            offset = y * self.line_size + x * (self.bits_per_pixel // 8) + i
            self.buffer_b[offset] = argb >> i * 8 & 0xFF

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


def run_mlx_3d(maze: Maze) -> None:
    """Run the 3d rendering."""
    renderer = Renderer(800, 600, "title - 3d", maze)
    renderer.run()
