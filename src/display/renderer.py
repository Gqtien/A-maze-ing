from functools import lru_cache
import signal
import time
import numpy
import numpy.typing as npt
from typing import Any
from pynput import keyboard
from mlx import Mlx  # type: ignore
from core import Maze
from utils import Vec2, Rect
from input import KeyboardHandler, MouseHandler, ChatHandler
from assets import Color, ColorPalette, CHAR_GLYPH_H
from display.camera import Camera, face_open_corridor
from display.raycasting import cast_ray
from display.drawing import (
    draw_horizontal_line,
    draw_rect,
    put_string,
    draw_player_sprite,
)
from display.playback import Playback
import threading


class Renderer:
    """MLX window, raycasts the maze grid, handles key input."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Create a renderer.

        create window and images,
        camera at entry facing a corridor,
        register mlx loop.
        """
        self.config: dict[str, Any] = config
        self.width: int = self.config.get("WIN_W", 1280)
        self.height: int = self.config.get("WIN_H", 720)
        self.title: str = self.config.get("WIN_TITLE", "A-Maze-Ing")
        self.fps: bool = self.config.get("FPS", True)
        self.maze: Maze = self._generate_maze()
        self._set_maze_state()

        self.keyboard_handler = KeyboardHandler()
        self.mouse_handler = MouseHandler()
        if self.config.get("MOUSE", False):
            self.mouse_handler.toggle()
        self.chat_handler = ChatHandler()
        self._esc_was_pressed: bool = False
        self.chat_handler.register_command(
            "regen", self._cmd_reset_maze, "regen <algo>"
        )
        self.chat_handler.register_command("solution", self._cmd_toggle_path)
        self.chat_handler.register_command(
            "play",
            self._cmd_play_solution,
            "play <speed=2.5>",
        )
        self.chat_handler.register_command("mouse", self._cmd_toggle_mouse)
        self.chat_handler.register_command("color", self._cmd_color)
        self.chat_handler.register_command("fps", self._cmd_toggle_fps)

        self.wall_palette: list[ColorPalette] = list(ColorPalette)
        self.wall_color_index: int = 0
        self.wall_color: bytes = self.wall_palette[self.wall_color_index].value
        self.pattern_color: bytes = self._darken_color(self.wall_color)
        self.pattern_core_color: bytes = self._lighten_color(
            self.pattern_color
        )
        self.solution_color: bytes = self.wall_palette[
            self.wall_color_index + 1
        ].value

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

        # precomputed chat background color buffer
        self.chat_bg_buffer: npt.NDArray[numpy.float32] = numpy.empty(
            (self.height - self.height // 2, self.width // 2, 3),
            dtype=numpy.float32,
        )

        # delta time and fps
        self.last_frame_time: int = time.perf_counter_ns()
        self.fps_value: float = 0.0
        self.fps_last_update_ns: int = time.perf_counter_ns()
        self.fps_frame_count: int = 0

        # minimap
        self.minimap_side: int = max(1, self.width // 4)
        self._compute_minimap()
        self._init_minimap()

        self._spawn_camera()
        self._init_playback()

    def _init_mlx(self) -> None:
        """Init and setup mlx: create mlx, window, register loop hook."""
        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.win_ptr = self.mlx.mlx_new_window(
            self.mlx_ptr, self.width, self.height, self.title
        )
        self.mlx.mlx_loop_hook(self.mlx_ptr, self.loop, param=None)

    def _generate_maze(self, algo: str = "backtracking") -> Maze:
        """Generate a Maze from current config."""
        return Maze(
            width=self.config.get("WIDTH", 25),
            height=self.config.get("HEIGHT", 25),
            entry_pos=self.config.get("ENTRY", (0, 0)),
            exit_pos=self.config.get("EXIT", (24, 24)),
            perfect=self.config.get("PERFECT", True),
            seed=self.config.get("SEED"),
            output_file_name=self.config.get("OUTPUT_FILE"),
            pattern=self.config.get("PATTERN"),
            algo=algo,
        )

    def _set_maze_state(self) -> None:
        """Set grid, entry/exit, pattern and dimensions from current maze."""
        self.grid = self.maze.to_grid()
        self.grid_entry_pos = (
            self.maze.entry_pos[0] * 2 + 1,
            self.maze.entry_pos[1] * 2 + 1,
        )
        self.grid_exit_pos = (
            self.maze.exit_pos[0] * 2 + 1,
            self.maze.exit_pos[1] * 2 + 1,
        )
        self.cells_pattern = {
            (cell.x, cell.y) for cell in self.maze.get_pattern_cells()
        }
        self.grid_width = len(self.grid[0])
        self.grid_height = len(self.grid)
        self.grid_solution_cells = self.maze.solution_to_grid()
        self.grid_pattern_cells = self.maze.pattern_to_grid()
        self.grid_pattern_core = self.maze.pattern_core_to_grid()
        self.show_solution = False

    def _compute_minimap(self) -> None:
        """Set minimap cell size and offsets."""
        self.minimap_cell_size = max(
            1,
            min(
                self.minimap_side // self.grid_width,
                self.minimap_side // self.grid_height,
            ),
        )
        self.minimap_offset_x = (
            self.minimap_side - self.grid_width * self.minimap_cell_size
        ) // 2
        self.minimap_offset_y = (
            self.minimap_side - self.grid_height * self.minimap_cell_size
        ) // 2

    def _init_minimap(self) -> None:
        """Create minimap image and buffers."""
        self.minimap_image, self.minimap_buffer = self._get_minimap()
        self.minimap_clear_buffer = bytes(self.minimap_buffer)
        self._minimap_np = numpy.frombuffer(
            self.minimap_buffer, dtype=numpy.uint8
        ).reshape(self.minimap_side, self.minimap_side, 4)

    def _get_minimap(self) -> tuple[Any, Any]:
        """Allocate a new MLX minimap image and draw grid cells into it."""
        minimap_image: int = self.mlx.mlx_new_image(
            self.mlx_ptr, self.minimap_side, self.minimap_side
        )
        minimap_buffer: memoryview
        minimap_buffer, _bpp, minimap_line_size, _ = (
            self.mlx.mlx_get_data_addr(minimap_image)
        )
        self._draw_minimap_cells(minimap_buffer, minimap_line_size)
        return minimap_image, minimap_buffer

    def _draw_minimap_cells(self, buffer: memoryview, line_size: int) -> None:
        """Fill buffer with floor then draw one rect per grid cell."""
        for i in range(0, buffer.nbytes, 4):
            buffer[i:i + 4] = Color.FLOOR.value
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
                    buffer,
                    line_size,
                )

    def _redraw_minimap(self) -> None:
        """Redraw minimap into existing buffer and update clear_buffer."""
        self._draw_minimap_cells(self.minimap_buffer, self.minimap_side * 4)
        self.minimap_clear_buffer = bytes(self.minimap_buffer)

    @staticmethod
    @lru_cache(maxsize=None)
    def _darken_color(color: bytes, percentage: int = 50) -> bytes:
        """Return a darker version of the color."""
        bgra: list[int] = list(color)
        for i in range(3):
            bgra[i] = bgra[i] * (100 - percentage) // 100
        return bytes(bgra)

    @staticmethod
    @lru_cache(maxsize=None)
    def _lighten_color(color: bytes, percentage: int = 85) -> bytes:
        """Return a lighter version of the color."""
        bgra: list[int] = list(color)
        for i in range(3):
            bgra[i] = bgra[i] + (255 - bgra[i]) * (100 - percentage) // 100
        return bytes(bgra)

    def _get_cell_color(self, x: int, y: int) -> bytes:
        """Return BGRA bytes for minimap cell at grid (x, y)."""
        if (x, y) in self.grid_pattern_core:
            return self.pattern_core_color
        if (x, y) in self.grid_pattern_cells:
            return self.pattern_color
        if self.grid[y][x]:
            return self.wall_color
        if (x, y) == self.grid_entry_pos:
            return Color.GREEN.value
        if (x, y) == self.grid_exit_pos:
            return Color.RED.value
        if self.show_solution and (x, y) in self.grid_solution_cells:
            return self.solution_color
        return Color.WHITE.value

    def _spawn_camera(self) -> None:
        """Place camera at maze entry facing an open corridor."""
        ex, ey = self.maze.entry_pos
        pos = Vec2(ex * 2 + 1.5, ey * 2 + 1.5)
        direction = face_open_corridor(self.grid, pos)
        self.camera = Camera(
            pos=pos,
            direction=direction,
            fov=self.config.get("FOV", 80),
            grid=self.grid,
            mode=self.config.get("MODE"),
        )

    def _init_playback(self) -> None:
        """Initialize the playback."""
        self.playback = Playback(self.camera, self.grid_solution_cells)

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
                wall_color=self.wall_color
            )
            perp_wall_dist = max(perp_wall_dist, 1e-6)
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

    def _render_player(self) -> None:
        """Draw the player sprite on the minimap."""
        player_color = (
            self.pattern_color
            if self.wall_color_index == 1
            else self._darken_color(ColorPalette.WHITE.value)
        )
        draw_player_sprite(
            camera_pos=(self.camera.pos.x, self.camera.pos.y),
            camera_dir=(self.camera.direction.x, self.camera.direction.y),
            cell_size=self.minimap_cell_size,
            offset_x=self.minimap_offset_x,
            offset_y=self.minimap_offset_y,
            buffer=self.minimap_buffer,
            line_size=self.minimap_side * 4,
            color=player_color,
        )

    def _render(self) -> None:
        """Render the maze.

        Draw sky and floor,
        cast one ray per column,
        put raycasting and minimap images to window.
        """

        # huge performance loss compared to numpy.fill
        self.numpy_raycasting_buffer[len(self.numpy_raycasting_buffer)//2:] = (
            list(self.pattern_color)
        )
        self.numpy_raycasting_buffer[:len(self.numpy_raycasting_buffer)//2] = (
            list(self._lighten_color(self.pattern_color, 95))
        )

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
            numpy.multiply(zone, 0.4, out=self.chat_bg_buffer)
            zone[:] = self.chat_bg_buffer
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

        if self.fps:
            put_string(
                f"FPS: {self.fps_value:.0f}",
                10,
                10,
                b"\xFF\xFF\xFF\xFF",
                self.numpy_raycasting_buffer,
            )

        self.mlx_raycasting_buffer[:] = self.numpy_raycasting_buffer.ravel()

        self.mlx.mlx_put_image_to_window(
            self.mlx_ptr, self.win_ptr, self.raycasting_image, 0, 0
        )

    def run(self) -> None:
        """Enter MLX event loop until exit or interrupt."""

        signal.signal(
            signal.SIGINT,
            lambda signum, frame: self.mlx.mlx_loop_exit(self.mlx_ptr),
        )
        self.mlx.mlx_loop(self.mlx_ptr)

    def loop(self, _: Any) -> None:
        """Render, update camera and dt."""
        now: int = time.perf_counter_ns()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        self.fps_frame_count += 1
        elapsed_ns = now - self.fps_last_update_ns
        if elapsed_ns >= 1_000_000_000:
            self.fps_value = self.fps_frame_count * 1e9 / elapsed_ns
            self.fps_frame_count = 0
            self.fps_last_update_ns = now

        chat_was_open = self.chat_handler.is_open
        self.chat_handler.update()
        if self.playback.is_playing:
            keys = self.keyboard_handler.keys_pressed
            move_keys = (
                self.camera.keys.forward,
                self.camera.keys.back,
                self.camera.keys.left,
                self.camera.keys.right,
                keyboard.Key.left,
                keyboard.Key.right,
            )
            if (
                any(k in keys for k in move_keys)
                or self.mouse_handler.peek_delta() != (0, 0)
            ):
                self.playback.stop()
        if not self.chat_handler.is_open:
            self.camera.move(dt)
        self._render()

        if (
            keyboard.Key.esc in self.keyboard_handler.keys_pressed
            and not self._esc_was_pressed
            and not chat_was_open
        ):
            self.quit()
        self._esc_was_pressed = (
            keyboard.Key.esc in self.keyboard_handler.keys_pressed
        )

    def _cmd_reset_maze(self, args: list[str]) -> tuple[str, bool]:
        """Regenerate the maze."""
        ALGOS = ("backtracking", "prim")
        if not args:
            return (
                f"Please provide an algo: /regen <{'|'.join(ALGOS)}>.",
                False,
            )
        algo = args[0].lower().strip()
        if algo not in ALGOS:
            return (
                f"Usage: /regen <{'|'.join(ALGOS)}>.",
                False,
            )
        self.playback.stop()
        self.maze = self._generate_maze(algo=algo)
        self._set_maze_state()
        self._compute_minimap()
        self.mlx.mlx_destroy_image(self.mlx_ptr, self.minimap_image)
        self._init_minimap()
        self._spawn_camera()
        self._init_playback()
        return (f"Maze regenerated with {algo}", True)

    def _cmd_color(self, args: list[str]) -> tuple[str, bool]:
        """Cycle wall/pattern/solution color through ColorPalette."""
        self.wall_color_index = (
            self.wall_color_index + 1
        ) % len(self.wall_palette)
        self.wall_color = self.wall_palette[self.wall_color_index].value
        self.pattern_color = self._darken_color(self.wall_color)
        self.pattern_core_color = self._lighten_color(self.pattern_color)
        self.solution_color = (
            self.wall_palette[self.wall_color_index + 1].value
            if self.wall_color_index == 1
            else ColorPalette.WHITE.value
        )
        self._redraw_minimap()
        return ("Changed the wall color", True)

    def _cmd_toggle_fps(self, args: list[str]) -> tuple[str, bool]:
        """Toggle FPS display."""
        self.fps = not self.fps
        return ("Toggled the FPS HUD", True)

    def _cmd_toggle_mouse(self, args: list[str]) -> tuple[str, bool]:
        """Toggle mouse input."""
        self.mouse_handler.toggle()
        return ("Toggled the mouse", True)

    def _cmd_toggle_path(self, args: list[str]) -> tuple[str, bool]:
        """Toggle path display."""
        self.show_solution = not self.show_solution
        self._compute_minimap()
        self.mlx.mlx_destroy_image(self.mlx_ptr, self.minimap_image)
        self._init_minimap()
        return ("Toggled the solution display", True)

    def _cmd_play_solution(self, args: list[str]) -> tuple[str, bool]:
        """Play the solution."""
        if self.playback.is_playing:
            self.playback.stop()
            return ("Stopped playing the solution", True)

        if len(args) > 1:
            return ("Usage: /play <speed=2.5>", False)

        speed = 2.5
        if args:
            try:
                speed = float(args[0])
            except ValueError:
                return ("Usage: /play <speed=2.5>", False)

        if speed <= 0.0:
            return ("Speed must be > 0. Usage: /play <speed=2.5>", False)

        self.playback.speed = speed
        thread = threading.Thread(
            target=self.playback.play_solution,
            daemon=True
        )
        thread.start()
        return (f"Started playing the solution (speed={speed:g})", True)

    def quit(self) -> None:
        """Properly exit mlx."""
        self.mlx.mlx_destroy_image(self.mlx_ptr, self.minimap_image)
        self.mlx.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
        self.mlx.mlx_destroy_image(self.mlx_ptr, self.raycasting_image)
        self.mlx.mlx_loop_exit(self.mlx_ptr)
