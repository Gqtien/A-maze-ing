import math
import time
import threading
from dataclasses import dataclass
from typing import Any
from libs.mlx.mlx import Mlx
from core.mazegen import Maze
from pynput import keyboard

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


class Camera:
    """First-person camera."""

    def __init__(self, pos: Vec2, direction: Vec2, fov: int) -> None:
        """Pos and direction in grid coords, FOV in degrees."""
        self.pos: Vec2 = pos
        self.direction: Vec2 = direction
        self.fov: int = fov
        self.fov_scale = math.tan(math.radians(self.fov) / 2)

        # Movement in units per second (independant from frame rate)
        self.move_speed: float = 2.5
        self.strafe_speed: float = 1.4
        self.rotate_speed: float = 2.0

        # Start the keyboard listener in a separate thread
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener_thread = threading.Thread(target=listener.start)
        listener_thread.daemon = True
        listener_thread.start()

    def move(self, delta_time_ns: int) -> None:
        """Move the camera."""
        # delta time in seconds
        dt: float = delta_time_ns / 1000000000.0

        if keyboard.Key.right in keys_pressed:
            self.direction.rotate(self.rotate_speed * dt)
        elif keyboard.Key.left in keys_pressed:
            self.direction.rotate(-self.rotate_speed * dt)

        # TODO: collisions
        if 'w' in keys_pressed:
            self.pos.x += self.direction.x * self.move_speed * dt
            self.pos.y += self.direction.y * self.move_speed * dt
        elif 's' in keys_pressed:
            self.pos.x -= self.direction.x * self.move_speed * dt
            self.pos.y -= self.direction.y * self.move_speed * dt

        if 'a' in keys_pressed:
            self.pos.x += self.direction.y * self.strafe_speed * dt
            self.pos.y -= self.direction.x * self.strafe_speed * dt
        elif 'd' in keys_pressed:
            self.pos.x -= self.direction.y * self.strafe_speed * dt
            self.pos.y += self.direction.x * self.strafe_speed * dt

    def get_rect(self, size: int) -> Rect:
        """Get a rect from the camera pos."""
        return Rect(
            int(self.pos.x * size) - size // 4,
            int(self.pos.y * size) - size // 4,
            size // 2,
            size // 2
        )


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
        fov: int,
        maze: Maze,
    ) -> None:
        """Create a renderer.

        create window and images,
        camera at entry facing a corridor,
        register mlx loop.
        """
        self.width: int = width
        self.height: int = height
        self.title: str = title
        self.maze: Maze = maze

        self._init_mlx()

        # a/b buffers for buffer swapping
        self.raycasting_image_a = self.mlx.mlx_new_image(
            self.mlx_ptr, self.width, self.height
        )
        self.raycasting_image_b = self.mlx.mlx_new_image(
            self.mlx_ptr, self.width, self.height
        )
        self.raycasting_buffer_a, _bits_per_pixel, self.line_size, _endian = (
            self.mlx.mlx_get_data_addr(self.raycasting_image_a)
        )
        self.raycasting_buffer_b, _bits_per_pixel, self.line_size, _endian = (
            self.mlx.mlx_get_data_addr(self.raycasting_image_b)
        )

        # colors in BGRA format (litte endian)
        floor_color: bytes = b'\x37\x37\x37\xFF'
        sky_color: bytes = b'\xEB\xCE\x87\xFF'

        # precomputed clearing buffer
        self.grid: list[list[bool]] = self.maze.to_grid()
        half_buffer_size: int = self.raycasting_buffer_b.nbytes // 2
        repeats = half_buffer_size // len(floor_color)
        self.clear_bytes: bytes = sky_color * repeats + floor_color * repeats

        # delta time
        self.last_frame_time: int = time.perf_counter_ns()

        # get cell size
        # TODO: make sure grid is not empty, also for other places in the code
        self.cell_size: int = min(
            self.width // len(self.grid),
            self.height // len(self.grid[0]),
        )

        # generate minimap
        self.minimap_image, self.minimap_buffer = self._get_minimap()
        self.minimap_clear_buffer: bytes = bytes(self.minimap_buffer)

        # Spawn camera
        ex, ey = self.maze.entry_pos
        pos: Vec2 = Vec2(ex * 3 + 1.5, ey * 3 + 1.5)
        direction: Vec2 = face_open_corridor(self.grid, pos)
        self.camera: Camera = Camera(
            pos=pos,
            direction=direction,
            fov=fov
        )

    def _init_mlx(self) -> None:
        """Init and setup mlx.

        create mlx, mlx pointer and windows,
        register loop function hook.
        """
        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.win_ptr = self.mlx.mlx_new_window(
            self.mlx_ptr, self.width * 2, self.height, self.title
        )
        self.mlx.mlx_loop_hook(self.mlx_ptr, self.loop, param=None)

    def _raycasting(self) -> None:
        """Cast on ray per column and draw a line for each ray."""
        for x in range(self.width):
            perp_wall_dist, is_horiz = self._cast_ray(x)
            line_height: int = int(self.height // perp_wall_dist)
            line_y: int = self.height // 2 - line_height // 2
            self.draw_vertical_line(
                y0=line_y,
                y1=line_y + line_height,
                x=x,
                argb=b'\xA0\xA0\xA0\xFF' if is_horiz else b'\x80\x80\x80\xFF'
            )

    def _get_minimap(self) -> tuple[Any, Any]:
        """Generate an minimap of the maze in an mlx image."""
        minimap_image: int = self.mlx.mlx_new_image(
            self.mlx_ptr, self.width, self.height
        )
        minimap_buffer: memoryview
        minimap_buffer, *_ = self.mlx.mlx_get_data_addr(minimap_image)

        # draw rects for each cell
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                cell_rect: Rect = Rect(
                    x * self.cell_size,
                    y * self.cell_size,
                    self.cell_size,
                    self.cell_size
                )
                self.draw_rect(
                    cell_rect, self._get_cell_color(x, y), minimap_buffer
                )
        return minimap_image, minimap_buffer

    def _get_cell_color(self, x: int, y: int) -> bytes:
        """Get cell color."""
        # NOTE: computed for every cell, could be optimized
        grid_entry_pos: tuple[int, int] = (
            self.maze.entry_pos[0] * 3 + 1, self.maze.entry_pos[1] * 3 + 1
        )
        grid_exit_pos: tuple[int, int] = (
            self.maze.exit_pos[0] * 3 + 1, self.maze.exit_pos[1] * 3 + 1
        )

        if self.grid[y][x]:
            return b'\xFF\xFF\xFF\xFF'
        elif (x, y) == grid_entry_pos:
            return b'\x00\xFF\x00\x7F'
        elif (x, y) == grid_exit_pos:
            return b'\x00\x00\xFF\x7F'
        return b'\x00\x00\x00\xFF'

    def _cast_ray(self, x: int) -> tuple[float, bool]:
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

    def _render_player(self) -> None:
        self.draw_rect(
            self.camera.get_rect(self.cell_size),
            b'\xFF\x90\xD0\xFF',
            self.minimap_buffer
        )

    def _render(self) -> None:
        """Render the maze.

        Draw sky and floor,
        cast one ray per column,
        put raycasting and minimap images to window,
        swap raycasting buffers,
        """
        # TODO: The visual should clearly show solution path.

        # clear
        self.raycasting_buffer_b[:] = self.clear_bytes
        self.minimap_buffer[:] = self.minimap_clear_buffer

        # render walls and player pos
        self._raycasting()
        self._render_player()

        # blit images to window
        self.mlx.mlx_put_image_to_window(
            self.mlx_ptr, self.win_ptr, self.raycasting_image_a, 0, 0
        )
        self.mlx.mlx_put_image_to_window(
            self.mlx_ptr, self.win_ptr, self.minimap_image, self.width, 0
        )

        # swap draw buffers
        self.raycasting_image_a, self.raycasting_image_b = \
            self.raycasting_image_b, self.raycasting_image_a
        self.raycasting_buffer_a, self.raycasting_buffer_b = \
            self.raycasting_buffer_b, self.raycasting_buffer_a

    def run(self) -> None:
        """Enter MLX event loop until exit."""
        self.mlx.mlx_loop(self.mlx_ptr)
        self.mlx.mlx_loop_exit(self.mlx_ptr)

    def loop(self, _: Any) -> None:
        """Render, update camera and dt."""
        now: int = time.perf_counter_ns()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        self.camera.move(dt)
        self._render()

        # TODO: User interactions must be available,
        # at least for the following tasks:
        # • Re-generate a new maze and display it.  NOTE: can be done from maze
        # • Show/Hide a valid shortest path from the entrance to the exit.
        #   - re-generate minimap maybe ?
        # • Change maze wall colours.
        # • Optional: set specific colours to display the “42” pattern.

        # user interactions
        # ESCAPE - quit
        if keyboard.Key.esc in keys_pressed:
            self.mlx.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
            self.mlx.mlx_destroy_image(self.mlx_ptr, self.raycasting_image_a)
            self.mlx.mlx_destroy_image(self.mlx_ptr, self.raycasting_image_b)
            self.mlx.mlx_loop_exit(self.mlx_ptr)

    def draw_vertical_line(
            self, y0: int, y1: int, x: int, argb: bytes
    ) -> None:
        """Draw a vertical line at x from y0 to y1."""
        # Skip out-of-bounds pixels
        y0 = max(0, y0)
        y1 = min(y1, self.height - 1)

        for y in range(y0, y1):
            offset = y * self.line_size + x * len(argb)
            self.raycasting_buffer_b[offset:offset + len(argb)] = argb

    def draw_rect(self, rect: Rect, argb: bytes, buffer: memoryview) -> None:
        """Draw a filled rectangle with a color."""
        for dx in range(rect.width):
            for dy in range(rect.height):
                self.put_pixel(rect.x + dx, rect.y + dy, argb, buffer)

    def put_pixel(
            self, x: int, y: int, argb: bytes, buffer: memoryview
    ) -> None:
        """Set one pixel in a buffer."""
        offset: int = y * self.line_size + x * len(argb)

        # Skip out-of-bounds pixels
        if offset >= len(buffer) - len(argb):
            return

        buffer[offset:offset + len(argb)] = argb
