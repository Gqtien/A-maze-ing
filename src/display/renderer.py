import time
from typing import Any
from libs.mlx.mlx import Mlx
from core.maze import Maze
from utils.geometry import Vec2, Rect
from input.keyboard import KeyboardHandler, keys_pressed
from display.constants import Color
from display.camera import Camera, face_open_corridor
from display.raycasting import cast_ray
from display.drawing import (
    draw_vertical_line,
    draw_rect,
    render_player_sprite
)
from pynput import keyboard


class Renderer:
    """MLX window, raycasts the maze grid, handles key input."""

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        fov: int,
        mode: str,
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
        self.grid_entry_pos: tuple[int, int] = (
            self.maze.entry_pos[0] * 3 + 1, self.maze.entry_pos[1] * 3 + 1
        )
        self.grid_exit_pos: tuple[int, int] = (
            self.maze.exit_pos[0] * 3 + 1, self.maze.exit_pos[1] * 3 + 1
        )

        # Initialize keyboard handler
        self._keyboard_handler = KeyboardHandler()

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

        # precomputed clearing buffer
        self.grid: list[list[bool]] = self.maze.to_grid()
        half_buffer_size: int = self.raycasting_buffer_b.nbytes // 2
        repeats = half_buffer_size // len(Color.FLOOR.value)
        self.clear_bytes: bytes = (
            Color.SKY.value * repeats + Color.FLOOR.value * repeats
        )

        # precomputed len
        self.grid_width: int = len(self.grid[0])
        self.grid_height: int = len(self.grid)

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
            fov=fov,
            grid=self.grid,
            mode=mode,
        )

    def _init_mlx(self) -> None:
        """Init and setup mlx.

        create mlx, mlx pointer and windows,
        register loop function hook.
        """
        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.win_ptr = self.mlx.mlx_new_window(
            self.mlx_ptr, self.width + self.height, self.height, self.title
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
            draw_vertical_line(
                y0=line_y,
                y1=line_y + line_height,
                x=x,
                height=self.height,
                argb=color,
                buffer=self.raycasting_buffer_b,
                line_size=self.line_size
            )

    def _get_minimap(self) -> tuple[Any, Any]:
        """Generate a minimap of the maze in an mlx image."""
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
                draw_rect(
                    cell_rect,
                    self._get_cell_color(x, y),
                    minimap_buffer,
                    self.line_size
                )
        return minimap_image, minimap_buffer

    def _get_cell_color(self, x: int, y: int) -> bytes:
        """Get cell color."""
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
            cell_size=self.cell_size,
            buffer=self.minimap_buffer,
            line_size=self.line_size
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
        # • Optional: set specific colours to display the "42" pattern.

        # user interactions
        # ESCAPE - quit
        if keyboard.Key.esc in keys_pressed:
            self.mlx.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
            self.mlx.mlx_destroy_image(self.mlx_ptr, self.raycasting_image_a)
            self.mlx.mlx_destroy_image(self.mlx_ptr, self.raycasting_image_b)
            self.mlx.mlx_loop_exit(self.mlx_ptr)
