import signal
import time
import numpy
from typing import Any
from pynput import keyboard
from libs.mlx.mlx import Mlx
from core import Maze, Mode
from utils import Vec2, Rect
from input import KeyboardHandler, ChatHandler
from assets import Color, CHAR_GLYPH_H
from display.camera import Camera, face_open_corridor
from display.raycasting import cast_ray
from display.drawing import (
    draw_horizontal_line,
    draw_rect,
    put_string,
    render_player_sprite,
)


class Renderer:
    """MLX window, raycasts the maze grid, handles key input."""

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        fov: int,
        mode: Mode,
        fps: bool,
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
        self.fps: bool = fps
        self.maze: Maze = maze
        self.grid_entry_pos: tuple[int, int] = (
            self.maze.entry_pos[0] * 3 + 1, self.maze.entry_pos[1] * 3 + 1
        )
        self.grid_exit_pos: tuple[int, int] = (
            self.maze.exit_pos[0] * 3 + 1, self.maze.exit_pos[1] * 3 + 1
        )
        self.cells_pattern: set[tuple[int, int]] = {
            (cell.x, cell.y) for cell in self.maze.get_pattern_cells()
        }

        self.keyboard_handler = KeyboardHandler()
        self.chat_handler = ChatHandler()
        self._esc_was_pressed: bool = False
        self.chat_handler.register_command("fps", self._cmd_toggle_fps)

        self._init_mlx()

        # mlx buffer
        self.raycasting_image = self.mlx.mlx_new_image(
            self.mlx_ptr, self.width, self.height
        )
        self.mlx_raycasting_buffer, _bits_per_pixel, self.line_size, _ = (
            self.mlx.mlx_get_data_addr(self.raycasting_image)
        )

        # numpy buffer
        assert self.line_size == self.width * 4, (
            f"Unexpected padding detected: "
            f"line_size={self.line_size}, expected={self.width * 4}"
        )
        self.numpy_raycasting_buffer = numpy.frombuffer(
            self.mlx_raycasting_buffer, dtype=numpy.uint8
        ).reshape(self.height, self.width, 4)

        # precomputed clearing buffer
        self.grid: list[list[bool]] = self.maze.to_grid()
        half_buffer_size: int = self.mlx_raycasting_buffer.nbytes // 2
        repeats = half_buffer_size // len(Color.FLOOR.value)
        self.clear_bytes: bytes = (
            Color.SKY.value * repeats + Color.FLOOR.value * repeats
        )

        # precomputed len
        self.grid_width: int = len(self.grid[0])
        self.grid_height: int = len(self.grid)

        # delta time and fps
        self.last_frame_time: int = time.perf_counter_ns()
        if self.fps:
            self.fps_value: float = 0.0
            self.fps_last_update_ns: int = time.perf_counter_ns()
            self.fps_frame_count: int = 0

        # get cell size for minimap
        self.minimap_side: int = self.width // 4
        self.minimap_cell_size: int = max(
            1,
            min(
                self.minimap_side // self.grid_width,
                self.minimap_side // self.grid_height,
            ),
        )
        self.minimap_offset_x: int = (
            self.minimap_side - self.grid_width * self.minimap_cell_size
        ) // 2
        self.minimap_offset_y: int = (
            self.minimap_side - self.grid_height * self.minimap_cell_size
        ) // 2
        self.minimap_image, self.minimap_buffer = self._get_minimap()
        self.minimap_clear_buffer: bytes = bytes(self.minimap_buffer)
        self._minimap_np = numpy.frombuffer(
            self.minimap_buffer, dtype=numpy.uint8
        ).reshape(self.minimap_side, self.minimap_side, 4)

        # Spawn camera
        ex, ey = self.maze.entry_pos
        pos: Vec2 = Vec2(ex * 3 + 1.5, ey * 3 + 1.5)
        direction: Vec2 = face_open_corridor(self.grid, pos)
        self.camera: Camera = Camera(
            pos=pos,
            direction=direction,
            fov=fov,
            grid=self.grid,
            mode=mode,
            keyboard_handler=self.keyboard_handler,
        )

    def _init_mlx(self) -> None:
        """Init and setup mlx.

        create mlx, mlx pointer and windows,
        register loop function hook.
        """
        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.win_ptr = self.mlx.mlx_new_window(
            self.mlx_ptr, self.width, self.height, self.title
        )
        self.mlx.mlx_loop_hook(self.mlx_ptr, self.loop, param=None)

    def _raycasting(self) -> None:
        """Cast one ray per column and draw a line for each ray."""
        for x in range(self.width):
            perp_wall_dist, color = cast_ray(
                x=x,
                width=self.width,
                camera_pos=(self.camera.pos.x, self.camera.pos.y),
                camera_dir=(self.camera.direction.x, self.camera.direction.y),
                fov_scale=self.camera.fov_scale,
                grid=self.grid,
                grid_width=self.grid_width,
                grid_height=self.grid_height,
                entry_pos=self.grid_entry_pos,
                exit_pos=self.grid_exit_pos,
            )
            line_height: int = int(self.height // perp_wall_dist)
            line_y: int = self.height // 2 - line_height // 2
            draw_horizontal_line(
                y0=line_y,
                y1=line_y + line_height,
                x=x,
                height=self.height,
                argb=color,
                numpy_buffer=self.numpy_raycasting_buffer,
            )

    def _get_minimap(self) -> tuple[Any, Any]:
        """Generate a minimap of the maze in an mlx image."""
        minimap_image: int = self.mlx.mlx_new_image(
            self.mlx_ptr, self.minimap_side, self.minimap_side
        )
        minimap_buffer: memoryview
        minimap_buffer, _bpp, minimap_line_size, _ = (
            self.mlx.mlx_get_data_addr(minimap_image)
        )

        for i in range(0, minimap_buffer.nbytes, 4):
            minimap_buffer[i:i + 4] = Color.FLOOR.value

        # draw rects for each cell
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                cell_rect = Rect(
                    x * self.minimap_cell_size + self.minimap_offset_x,
                    y * self.minimap_cell_size + self.minimap_offset_y,
                    self.minimap_cell_size,
                    self.minimap_cell_size,
                )
                draw_rect(
                    cell_rect,
                    self._get_cell_color(x, y),
                    minimap_buffer,
                    minimap_line_size,
                )
        return minimap_image, minimap_buffer

    def _get_cell_color(self, x: int, y: int) -> bytes:
        """Get cell color."""
        maze_x, maze_y = x // 3, y // 3
        if (maze_x, maze_y) in self.cells_pattern:
            return Color.PATTERN.value
        if self.grid[y][x]:
            return Color.BLACK.value
        elif (x, y) == self.grid_entry_pos:
            return Color.GREEN.value
        elif (x, y) == self.grid_exit_pos:
            return Color.RED.value
        return Color.WHITE.value

    def _render_player(self) -> None:
        """Draw the player sprite on the minimap."""
        render_player_sprite(
            camera_pos=(self.camera.pos.x, self.camera.pos.y),
            camera_dir=(self.camera.direction.x, self.camera.direction.y),
            cell_size=self.minimap_cell_size,
            offset_x=self.minimap_offset_x,
            offset_y=self.minimap_offset_y,
            buffer=self.minimap_buffer,
            line_size=self.minimap_side * 4,
        )

    def _render(self) -> None:
        """Render the maze.

        Draw sky and floor,
        cast one ray per column,
        put raycasting and minimap images to window.
        """
        # TODO: The visual should clearly show solution path.

        self.numpy_raycasting_buffer.fill(200)
        self.minimap_buffer[:] = self.minimap_clear_buffer

        # render walls
        self._raycasting()
        # minimap blit on top-right of main buffer
        self._render_player()
        x0 = self.width - self.minimap_side
        self.numpy_raycasting_buffer[0:self.minimap_side, x0:self.width, :] = (
            self._minimap_np
        )

        if self.chat_handler.is_open:
            zone = self.numpy_raycasting_buffer[
                self.height // 2:,
                :self.width // 2,
                :3,
            ]
            zone[:] = zone * 0.4

        if self.fps:
            put_string(
                f"FPS: {self.fps_value:.0f}",
                10,
                10,
                b"\xFF\xFF\xFF\xFF",
                self.numpy_raycasting_buffer,
            )

        if self.chat_handler.is_open:
            line_height = CHAR_GLYPH_H
            grey_zone_height = self.height - 20 - self.height // 2
            max_message_lines = max(0, grey_zone_height // line_height)
            lines = self.chat_handler.get_overlay_lines(max_message_lines)
            for i, (text, color_bgra) in enumerate(lines):
                y = self.height - 20 - line_height * (len(lines) - 1 - i)
                put_string(
                    text,
                    10,
                    y,
                    color_bgra,
                    self.numpy_raycasting_buffer,
                )

        self.mlx_raycasting_buffer[:] = self.numpy_raycasting_buffer.ravel()

        self.mlx.mlx_put_image_to_window(
            self.mlx_ptr, self.win_ptr, self.raycasting_image, 0, 0
        )

    def run(self) -> None:
        """Enter MLX event loop until exit or interrupt."""

        signal.signal(signal.SIGINT, self.mlx.mlx_loop_exit(self.mlx_ptr))
        self.mlx.mlx_loop(self.mlx_ptr)

    def loop(self, _: Any) -> None:
        """Render, update camera and dt."""
        now: int = time.perf_counter_ns()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        if self.fps:
            self.fps_frame_count += 1
            elapsed_ns = now - self.fps_last_update_ns
            if elapsed_ns >= 1_000_000_000:
                self.fps_value = self.fps_frame_count * 1e9 / elapsed_ns
                self.fps_frame_count = 0
                self.fps_last_update_ns = now

        chat_was_open = self.chat_handler.is_open
        self.chat_handler.update()
        if not self.chat_handler.is_open:
            self.camera.move(dt)
        self._render()

        # TODO: User interactions must be available,
        # at least for the following tasks:
        # • Re-generate a new maze and display it.  NOTE: can be done from maze
        # • Show/Hide a valid shortest path from the entrance to the exit.
        #   - re-generate minimap maybe ?
        # • Change maze wall colours.
        # • Optional: set specific colours to display the "42" pattern.

        if (
            keyboard.Key.esc in self.keyboard_handler.keys_pressed
            and not self._esc_was_pressed
            and not chat_was_open
        ):
            self.quit()
        self._esc_was_pressed = (
            keyboard.Key.esc in self.keyboard_handler.keys_pressed
        )

    def _cmd_toggle_fps(self) -> None:
        """Toggle FPS display."""
        self.fps = not self.fps

    def quit(self) -> None:
        """Properly exit mlx."""
        self.mlx.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
        self.mlx.mlx_destroy_image(self.mlx_ptr, self.raycasting_image)
        self.mlx.mlx_loop_exit(self.mlx_ptr)
