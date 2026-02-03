import sys
from src.core.mazegen import Maze, Wall


def maze_to_bool_grid(maze: Maze) -> list[list[bool]]:
    """Convert maze to a (2*height+1) x (2*width+1) grid."""
    h, w = maze.height, maze.width
    rows = maze.rows()
    grid: list[list[bool]] = [
        [False] * (2 * w + 1)
        for _ in range(2 * h + 1)
    ]
    for iy in range(h):
        for jx in range(w):
            val = rows[iy][jx].wall
            n = (val & Wall.NORTH.value) != 0
            w_ = (val & Wall.WEST.value) != 0

            grid[2 * iy][2 * jx + 1] = n
            grid[2 * iy + 1][2 * jx] = w_
            grid[2 * iy][2 * jx] = n or w_

    for jx in range(w):
        grid[2 * h][2 * jx + 1] = (rows[h - 1][jx].wall & Wall.SOUTH.value) != 0
        grid[2 * h][2 * jx] = (
            rows[h - 1][jx].wall & (Wall.SOUTH.value | Wall.WEST.value)
        ) != 0

    for iy in range(h):
        grid[2 * iy + 1][2 * w] = (rows[iy][w - 1].wall & Wall.EAST.value) != 0
    grid[0][2 * w] = (rows[0][w - 1].wall & Wall.NORTH.value) != 0 or (rows[0][w - 1].wall & Wall.EAST.value) != 0
    
    for iy in range(1, h):
        grid[2 * iy][2 * w] = (
            (rows[iy - 1][w - 1].wall & Wall.EAST.value) != 0
            or (rows[iy][w - 1].wall & Wall.NORTH.value) != 0
        )

    grid[2 * h][2 * w] = (rows[h - 1][w - 1].wall & (Wall.SOUTH.value | Wall.EAST.value)) != 0
    
    return grid


def render_ascii(maze: Maze) -> None:
    """Print maze as 2D wall grid."""
    grid = maze_to_bool_grid(maze)
    for line in grid:
        for cell in line:
            print('██' if cell else "  ", end="")
        print()
