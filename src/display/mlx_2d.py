from typing import Any
from libs.mlx.mlx import Mlx
from core.mazegen import Maze
from dataclasses import dataclass
from pynput import keyboard
import threading


keys_pressed: set[str | keyboard.Key] = set()


def on_press(key: keyboard.Key) -> None:
    try:
        keys_pressed.add(key.char)
    except AttributeError:
        keys_pressed.add(key)


def on_release(key: keyboard.Key) -> None:
    try:
        keys_pressed.discard(key.char)
    except AttributeError:
        keys_pressed.discard(key)


@dataclass
class Rect:
    """Rectangle in pixel coordinates (x, y, width, height)."""

    x: int
    y: int
    width: int
    height: int


class Map2D:
    """2D top-down maze view."""
    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        entry: tuple[int, int],
        exit: tuple[int, int],
        maze: Maze,
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.entry: tuple[int, int] = entry
        self.exit: tuple[int, int] = exit
        self.maze: Maze = maze
        self.grid: list[list[bool]] = self.maze.to_grid()
        self.ncols: int = len(self.grid[0]) if self.grid else 0
        self.nrows: int = len(self.grid)

        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.win_ptr = self.mlx.mlx_new_window(
            self.mlx_ptr, width, height, title
        )
        self.img_ptr = self.mlx.mlx_new_image(self.mlx_ptr, width, height)
        self.buffer, self.bits_per_pixel, self.line_size, _endian = (
            self.mlx.mlx_get_data_addr(self.img_ptr)
        )

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener_thread = threading.Thread(target=listener.start)
        listener_thread.daemon = True
        listener_thread.start()

        self.mlx.mlx_loop_hook(self.mlx_ptr, self.loop, param=None)

        self.color_wall = 0xFF404040
        self.color_empty = 0xFFFFFFFF
        self.color_entry = 0xFF00AA00
        self.color_exit = 0xFF0000CC

    def draw_rect(self, rect: Rect, argb: int) -> None:
        """Fill rectangle with a color."""
        for dx in range(rect.width):
            for dy in range(rect.height):
                self.put_pixel(rect.x + dx, rect.y + dy, argb)

    def put_pixel(self, x: int, y: int, argb: int) -> None:
        """Set one pixel."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        offset = y * self.line_size + x * 4
        self.buffer[offset:offset + 4] = argb.to_bytes(4, "little")

    def cell_color(self, col: int, row: int) -> int:
        """Return ARGB color for cell (col, row)."""
        if self.grid[row][col]:
            return self.color_wall
        if (col, row) == self.entry:
            return self.color_entry
        if (col, row) == self.exit:
            return self.color_exit
        return self.color_empty

    def render(self) -> None:
        """Draw maze grid and put image to window."""
        if self.nrows == 0 or self.ncols == 0:
            self.mlx.mlx_put_image_to_window(
                self.mlx_ptr, self.win_ptr, self.img_ptr, 0, 0
            )
            return

        scale = min(
            self.width / self.ncols,
            self.height / self.nrows,
        )
        if scale <= 0:
            scale = 1.0

        draw_w = self.ncols * scale
        draw_h = self.nrows * scale
        offset_x = (self.width - draw_w) / 2
        offset_y = (self.height - draw_h) / 2

        for py in range(self.height):
            for px in range(self.width):
                cell_x = (px - offset_x) / scale
                cell_y = (py - offset_y) / scale

                if 0 <= cell_x < self.ncols and 0 <= cell_y < self.nrows:
                    col, row = int(cell_x), int(cell_y)
                    self.put_pixel(px, py, self.cell_color(col, row))

        self.mlx.mlx_put_image_to_window(
            self.mlx_ptr, self.win_ptr, self.img_ptr, 0, 0
        )

    def loop(self, _: Any) -> None:
        """Called each frame: render and check Esc to exit."""
        self.render()
        if keyboard.Key.esc in keys_pressed:
            self.mlx.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
            self.mlx.mlx_destroy_image(self.mlx_ptr, self.img_ptr)
            self.mlx.mlx_loop_exit(self.mlx_ptr)

    def run(self) -> None:
        """Enter MLX event loop until exit."""
        self.mlx.mlx_loop(self.mlx_ptr)
        self.mlx.mlx_loop_exit(self.mlx_ptr)


def run_mlx_2d(maze: Maze, settings: dict[str, Any]) -> None:
    """Create 2D map from maze and settings, then run the view."""
    map = Map2D(
        settings["WIN_W"],
        settings["WIN_H"],
        settings["WIN_TITLE"],
        settings["ENTRY"],
        settings["EXIT"],
        maze,
    )
    map.run()
