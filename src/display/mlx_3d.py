import math
import time
from dataclasses import dataclass
from typing import Any
from libs.mlx.mlx import Mlx
from core.mazegen import Maze
from pynput import keyboard
import threading

# Global variables to track key states
keys_pressed: set[str | keyboard.Key] = set()


def on_press(key: keyboard.Key) -> None:
    """Key press callback."""
    try:
        keys_pressed.add(key.char)
    except AttributeError:
        keys_pressed.add(key)


def on_release(key: keyboard.Key) -> None:
    """Key release callback."""
    try:
        keys_pressed.remove(key.char)
    except AttributeError:
        keys_pressed.remove(key)
    except KeyError:
        pass


class Vec2:
    """2D vector."""

    def __init__(self, x: float, y: float) -> None:
        """Store x, y."""
        self.x: float = x
        self.y: float = y

    def __eq__(self, other: object) -> bool:
        """True if other is a Vec2 with same x and y."""
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


class Camera:
    """First-person camera."""

    def __init__(self, pos: Vec2, direction: Vec2, FOV: int) -> None:
        """pos and direction in grid coords, FOV in degrees."""
        self.pos: Vec2 = pos
        self.direction: Vec2 = direction
        self.FOV: int = FOV
        self.fov_scale = math.tan(math.radians(self.FOV) / 2)

        # Movement in units per second (independant from frame rate)
        self.move_speed: float = 2.5
        self.strafe_speed: float = 1.4
        self.rotate_speed: float = 2.0

        # Start the keyboard listener in a separate thread
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener_thread = threading.Thread(target=listener.start)
        listener_thread.daemon = True
        listener_thread.start()

    def move(self, dt: float) -> None:
        """Move the camera. dt = time since last frame in seconds."""
        dt = min(dt, 0.1)

        if keyboard.Key.right in keys_pressed:
            self.direction.rotate(self.rotate_speed * dt)
        elif keyboard.Key.left in keys_pressed:
            self.direction.rotate(-self.rotate_speed * dt)

        # TODO: collisions
        if 'z' in keys_pressed:
            self.pos.x += self.direction.x * self.move_speed * dt
            self.pos.y += self.direction.y * self.move_speed * dt
        elif 's' in keys_pressed:
            self.pos.x -= self.direction.x * self.move_speed * dt
            self.pos.y -= self.direction.y * self.move_speed * dt

        if 'q' in keys_pressed:
            self.pos.x += self.direction.y * self.strafe_speed * dt
            self.pos.y -= self.direction.x * self.strafe_speed * dt
        elif 'd' in keys_pressed:
            self.pos.x -= self.direction.y * self.strafe_speed * dt
            self.pos.y += self.direction.x * self.strafe_speed * dt


def face_open_corridor(grid: list[list[bool]], pos: Vec2) -> Vec2:
    """First cardinal (E/W/N/S) from pos that points to a non-wall cell."""
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = int(pos.x + dx), int(pos.y + dy)
        if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]) and not grid[ny][nx]:
            return Vec2(dx, dy)
    return Vec2(1, 0)


class Renderer:
    """MLX window, raycasts the maze grid, handles key input."""

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
        """Create window and images,
           camera at entry facing a corridor,
           register loop and key hooks.
        """
        self.width: int = width
        self.height: int = height
        self.title: str = title
        self.maze: Maze = maze

        self.grid: list[list[bool]] = self.maze.to_grid()
        ex, ey = entry
        pos: Vec2 = Vec2(ex * 3 + 1.5, ey * 3 + 1.5)
        direction: Vec2 = face_open_corridor(self.grid, pos)
        self.camera: Camera = Camera(pos=pos, direction=direction, FOV=FOV)

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

        # precomputed values
        self.half_buffer_size: int = self.buffer_b.nbytes // 2
        floor_color: bytes = b'\x67\x67\x67\xFF'  # BGRA, litte endian
        sky_color: bytes = b'\xEB\xCE\x87\xFF'
        self.blue: bytes = b'\xFF\x00\x00\xFF'
        self.red: bytes = b'\x00\x00\xFF\xFF'
        repeats = self.half_buffer_size // len(floor_color)
        self.sky: bytes = sky_color * repeats
        self.floor: bytes = floor_color * repeats

        self.last_frame_time: float = time.perf_counter()

    def render(self) -> None:
        """
           Draw sky and floor,
           cast one ray per column,
           then swap buffers and put image to window.
        """
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
        plane_x = -self.camera.direction.y * self.camera.fov_scale
        plane_y = self.camera.direction.x * self.camera.fov_scale

        camera_x: float = 2 * x / self.width - 1  # x in [-1; 1]

        ray_dir_x: float = self.camera.direction.x + plane_x * camera_x
        ray_dir_y: float = self.camera.direction.y + plane_y * camera_x

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

            # clamp map indexes
            if map_x < 0 or map_y < 0:
                break
            if map_x >= len(self.grid[0]) - 1 or map_y >= len(self.grid) - 1:
                break
            hit = self.grid[map_y][map_x]

        perp_wall_dist: float = dist_x - dx if is_vertical else dist_y - dy
        return perp_wall_dist, is_vertical

    def run(self) -> None:
        """Enter MLX event loop until exit."""
        self.mlx.mlx_loop(self.mlx_ptr)
        self.mlx.mlx_loop_exit(self.mlx_ptr)

    def loop(self, _: Any) -> None:
        """Called each frame: render then update camera."""
        now = time.perf_counter()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        self.render()
        self.camera.move(dt)
        if keyboard.Key.esc in keys_pressed:
            self.mlx.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
            self.mlx.mlx_destroy_image(self.mlx_ptr, self.img_ptr_a)
            self.mlx.mlx_destroy_image(self.mlx_ptr, self.img_ptr_b)
            self.mlx.mlx_loop_exit(self.mlx_ptr)

    def clear(self) -> None:
        """Clear the memory buffer."""
        self.buffer_b[:] = b"\x00" * self.buffer_b.nbytes

    def draw_vertical_line(
            self, y0: int, y1: int, x: int, argb: bytes
    ) -> None:
        """Draw a vertical line at x from y0 to y1."""
        # Skip out-of-bounds pixels
        y0 = max(0, y0)
        y1 = min(y1, self.height - 1)

        for y in range(y0, y1):
            offset = y * self.line_size + x * 4
            self.buffer_b[offset:offset + 4] = argb

    def draw_rect(self, rect: Rect, argb: int) -> None:
        """Fill rectangle with a color."""
        for dx in range(rect.width):
            for dy in range(rect.height):
                self.put_pixel(rect.x + dx, rect.y + dy, argb)

    def put_pixel(self, x: int, y: int, argb: int) -> None:
        """Set one pixel."""
        # Skip out-of-bounds pixels
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        offset = y * self.line_size + x * 4
        self.buffer_b[offset:offset + 4] = argb.to_bytes(4, 'little')


def run_mlx_3d(maze: Maze, settings: dict[str, Any]) -> None:
    """Create renderer from maze and settings, then run the 3D view."""
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
