from src.core.mazegen import Maze, Wall


def maze_to_bool_grid(maze: Maze) -> list[list[bool]]:
    """Convert maze to a 3x-per-cell grid for wall drawing (True = wall)."""
    grid: list[list[bool]] = []
    rows = maze.get_maze()
    for y, line in enumerate(rows):
        for i in range(3):
            grid.append([])
            for cell in line:
                val = cell.wall
                match i:
                    case 0:
                        grid[y * 3 + i].append(
                            (val & Wall.NORTH.value > 0)
                            or (val & Wall.WEST.value > 0)
                        )
                        grid[y * 3 + i].append(val & Wall.NORTH.value > 0)
                        grid[y * 3 + i].append(
                            (val & Wall.NORTH.value > 0)
                            or (val & Wall.EAST.value > 0)
                        )
                    case 1:
                        grid[y * 3 + i].append(val & Wall.WEST.value > 0)
                        grid[y * 3 + i].append(
                            (val & Wall.NORTH.value > 0)
                            and (val & Wall.WEST.value > 0)
                            and (val & Wall.EAST.value > 0)
                            and (val & Wall.SOUTH.value > 0)
                        )
                        grid[y * 3 + i].append(val & Wall.EAST.value > 0)
                    case 2:
                        grid[y * 3 + i].append(
                            (val & Wall.SOUTH.value > 0)
                            or (val & Wall.WEST.value > 0)
                        )
                        grid[y * 3 + i].append(val & Wall.SOUTH.value > 0)
                        grid[y * 3 + i].append(
                            (val & Wall.SOUTH.value > 0)
                            or (val & Wall.EAST.value > 0)
                        )
    return grid


def render_ascii(maze: Maze) -> None:
    """Print maze as 2D wall grid then hex row lines."""
    grid = maze_to_bool_grid(maze)
    for line in grid:
        for cell in line:
            print('██' if cell else "  ", end="")
        print()
