"""Render (print) an ascii version of the maze."""

from core.mazegen import Maze


def render_ascii(maze: Maze) -> None:
    """Print maze as 2D wall grid."""
    grid = maze.to_grid()
    for line in grid:
        for cell in line:
            print('██' if cell else "  ", end="")
        print()
