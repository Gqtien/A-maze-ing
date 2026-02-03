#!/usr/bin/env python3

import random
import time
from enum import Enum
import mlx


class Wall(Enum):
    """Wall bitmasks."""

    NORTH = 1 << 0  # 1
    EAST  = 1 << 1  # 2
    SOUTH = 1 << 2  # 4
    WEST  = 1 << 3  # 8


class Cell:
    """Maze cell."""

    def __init__(self, x: int, y: int, walls: int = 0) -> None:
        """Init."""
        self.wall: int = walls
        self.x: int = x
        self.y: int = y

    def __repr__(self) -> str:
        """Repr."""
        return hex(self.wall)[2:]


class Maze:
    """Maze."""

    def __init__(
        self,
        width: int,
        height: int,
        seed: int,
        entry: tuple[int, int],
        exit: tuple[int, int],
        perfect: bool,
        output_file_name: str | None = None
    ) -> None:
        """Create a maze."""
        # TODO: config file
        self.width: int = width
        self.height: int = height
        self.seed: int = seed
        self.entry: tuple[int, int] = entry
        self.exit: tuple[int, int] = exit
        self.perfect: bool = perfect
        self.output_file_name: str | None = output_file_name
        self._maze: list[list[Cell]] = []

        for y in range(self.height):
            self._maze.append([])
            for x in range(self.width):
                self._maze[y].append(Cell(x, y, 15))

    def generate(
            self, x: int, y: int, rng: random.Random, visited: list[Cell] = []
    ) -> None:
        """Generate a maze using recursive backtracking."""
        current_cell = self._maze[y][x]
        visited.append(current_cell)

        neighbors = self.get_neighbors(current_cell)
        rng.shuffle(neighbors)

        for neighbor in neighbors:
            if neighbor in visited:
                continue
            self.remove_wall(current_cell, neighbor)
            self.generate(neighbor.x, neighbor.y, visited)

    def __str__(self) -> str:
        """Str."""
        ret: str = ""
        for y in range(self.height):
            for x in range(self.width):
                ret += str(self._maze[y][x])
            ret += '\n'
        return ret

    def get_neighbors(self, cell: Cell) -> list[Cell]:
        """Get neighbors of a cell."""
        ret: list[Cell] = []
        for dx, dy in (-1, 0), (1, 0), (0, 1), (0, -1):
            x, y = cell.x + dx, cell.y + dy
            if x < 0 or y < 0:
                continue
            if x >= self.width or y >= self.height:
                continue
            ret.append(self._maze[y][x])
        return ret

    def remove_wall(self, cell1: Cell, cell2: Cell) -> None:
        """Open path between two cell."""
        dx = cell2.x - cell1.x
        dy = cell2.y - cell1.y
        match dx, dy:
            case 1, 0:
                # print("east")
                cell1.wall &= ~Wall.EAST.value
                cell2.wall &= ~Wall.WEST.value
            case 0, 1:
                # print("south")
                cell1.wall &= ~Wall.SOUTH.value
                cell2.wall &= ~Wall.NORTH.value
            case -1, 0:
                # print("ouest")
                cell1.wall &= ~Wall.WEST.value
                cell2.wall &= ~Wall.EAST.value
            case 0, -1:
                # print("nord")
                cell1.wall &= ~Wall.NORTH.value
                cell2.wall &= ~Wall.SOUTH.value

    def to_bool_grid(self) -> list[list[bool]]:
        """Convert walls to a grid of cell."""
        grid: list[list[bool]] = []
        for y, line in enumerate(self._maze):
            for i in range(3):
                grid.append([])
                for char in line:
                    val = char.wall
                    match i:
                        case 0:
                            grid[y * 3 + i].append(val & Wall.NORTH.value > 0
                                                   or val & Wall.WEST.value > 0)
                            grid[y * 3 + i].append(val & Wall.NORTH.value > 0)
                            grid[y * 3 + i].append(val & Wall.NORTH.value > 0
                                                   or val & Wall.EAST.value > 0)
                        case 1:
                            grid[y * 3 + i].append(val & Wall.WEST.value > 0)
                            grid[y * 3 + i].append(val & Wall.NORTH.value > 0
                                                   and val & Wall.WEST.value > 0
                                                   and val & Wall.EAST.value > 0
                                                   and val & Wall.SOUTH.value > 0)
                            grid[y * 3 + i].append(val & Wall.EAST.value > 0)
                        case 2:
                            grid[y * 3 + i].append(val & Wall.SOUTH.value > 0
                                                   or val & Wall.WEST.value > 0)
                            grid[y * 3 + i].append(val & Wall.SOUTH.value > 0)
                            grid[y * 3 + i].append(val & Wall.SOUTH.value > 0
                                                   or val & Wall.EAST.value > 0)
        return grid

    def print(self) -> None:
        """Print a 2D repr of the maze."""
        grid = self.to_bool_grid()
        for line in grid:
            for cell in line:
                print('█' if cell else ' ', end='')
            print()
        print()
        print(self)


def loop(mlx_ptr) -> None:
    """Loop."""
    for x in range(100):
        for y in range(100):
            mlx.mlx_pixel_put(mlx_ptr, win_ptr, 500 + x, y, 0xffff0000)
    mlx.mlx_put_image_to_window(mlx_ptr, win_ptr, image, 0, 0)


def key_hook(key, mlx_ptr: int) -> None:
    """Keyboard events."""
    match key:
        case 65307:
            mlx.mlx_loop_exit(mlx_ptr)
        case _:
            print("called key:", key)


if __name__ == "__main__":
    # maze = Maze(10_000, 10_000, 0, (0, 0), (0, 0), False)
    # maze.generate(0, 0)
    # maze.print()

    mlx = mlx.Mlx()
    mlx_ptr = mlx.mlx_init()
    win_ptr = mlx.mlx_new_window(mlx_ptr, 1920, 1080, "67")
    image = mlx.mlx_new_image(mlx_ptr, 1920, 1080)

    mlx.mlx_loop_hook(mlx_ptr, loop, param=mlx_ptr)
    mlx.mlx_key_hook(win_ptr, key_hook, param=mlx_ptr)

    mlx.mlx_loop(mlx_ptr)
