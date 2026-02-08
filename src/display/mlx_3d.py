"""Wolfenstein-like fake 3D raytraced rendering."""

from libs.mlx.mlx import Mlx
from typing import Any
from src.core.mazegen import Maze
from dataclasses import dataclass
import math


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

    def length(self) -> float:
        """Get length."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self) -> None:
        """Make lenght 1."""
        length = self.length()
        self.x /= length
        self.y /= length


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
    direction: Vec2 = Vec2(1.0, 0.0)
    FOV: int = 100
    speed: int = 10  # pixels/frame

    def move(self, keys: set[int]) -> None:
        """Move the camera."""
        if 65363 in keys:  # right arrow
            self.pos.x += self.speed
        if 65364 in keys:  # down arrow
            self.pos.y += self.speed
        if 65361 in keys:  # left arrow
            self.pos.x -= self.speed
        if 65362 in keys:  # up arrow
            self.pos.y -= self.speed


class Renderer:
    """Wrap mlx."""

    def __init__(self, width: int, height: int, title: str, maze: Maze) -> None:
        """Init the mlx, hook functions."""
        self.width: int = width
        self.height: int = height
        self.time: str = title

        # mlx
        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.win_ptr = self.mlx.mlx_new_window(self.mlx_ptr, width, height, title)
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
        self.camera: Camera = Camera(Vec2(10, 10))  # TODO: init pos
        self.keys: set[int] = set()

        self.mlx.mlx_do_sync(self.mlx_ptr)

    def render(self) -> None:
        """Render."""
        line_width: int = 5
        for x in range(0, self.width, line_width):
            perp_wall_dist: float = self.cast_ray(x)
            if perp_wall_dist < 0.01:
                perp_wall_dist = 1.0
            line_height: int = int(self.height // perp_wall_dist)
            line_y: int = self.height // 2 - line_height // 2
            # print(line_height)
            # print(perp_wall_dist)
            self.draw_rect(Rect(x, line_y, line_width, line_height), 0xFFFF0000)

    def cast_ray(self, x: int) -> float:
        """Get the distance from a wall in a dir."""
        ray: Vec2 = self.camera.pos
        start_dir = self.camera.direction
        hit = False
        while not hit:
            ray.x += 0.1
            ray.y += 0.1
            map_x = round(ray.x)
            map_y = round(ray.y)
            if map_x <= 0 or map_y <= 0:
                break
            if map_x >= self.maze.width - 1 or map_y >= self.maze.height - 1:
                break
            # TODO: check depending on incoming direction
            hit = self.maze._maze[map_y][map_x].is_full()
        dist = math.sqrt((ray.x - map_x) ** 2 + (ray.y - map_y) ** 2)
        if dist < 0.01:
            dist = 0.0
        return dist

    def run(self) -> None:
        """Start infinite loop."""
        self.mlx.mlx_loop(self.mlx_ptr)
        self.mlx.mlx_loop_exit(self.mlx_ptr)

    def loop(self, _: Any) -> None:
        """Loop."""
        self.clear()

        self.render()

        self.mlx.mlx_put_image_to_window(
            self.mlx_ptr, self.win_ptr, self.img_ptr_a, 0, 0
        )
        self.mlx.mlx_sync(self.mlx_ptr, 0, self.win_ptr)

        # swap draw buffers
        self.img_ptr_a, self.img_ptr_b = self.img_ptr_b, self.img_ptr_a
        self.buffer_a, self.buffer_b = self.buffer_b, self.buffer_a

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
        if key == 65293:  # ENTER
            return  # skip first enter key up after lauching the command
        self.keys.remove(key)


def run_mlx_3d(maze) -> None:
    """Run the 3d rendering."""
    renderer = Renderer(800, 600, "title - 3d", maze)
    renderer.run()
