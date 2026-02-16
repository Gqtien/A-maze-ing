"""Module for generating a maze."""

import random
from enum import Enum


class Wall(Enum):
    """Wall bitmasks."""

    NORTH = 1 << 0
    EAST = 1 << 1
    SOUTH = 1 << 2
    WEST = 1 << 3


class Cell:
    """Maze cell with wall bitmask."""

    def __init__(self, x: int, y: int, walls: int = 0) -> None:
        """Init cell."""
        self.wall: int = walls
        self.x: int = x
        self.y: int = y

    def __repr__(self) -> str:
        """Hex value."""
        return hex(self.wall)[2:].upper()

    def north(self) -> bool:
        """Get north wall."""
        return self.wall & Wall.NORTH.value == Wall.NORTH.value

    def south(self) -> bool:
        """Get south wall."""
        return self.wall & Wall.SOUTH.value == Wall.SOUTH.value

    def east(self) -> bool:
        """Get east wall."""
        return self.wall & Wall.EAST.value == Wall.EAST.value

    def west(self) -> bool:
        """Get west wall."""
        return self.wall & Wall.WEST.value == Wall.WEST.value

    def nw(self) -> bool:
        """North or West."""
        return self.north() or self.west()

    def ne(self) -> bool:
        """North or east."""
        return self.north() or self.east()

    def sw(self) -> bool:
        """South or west."""
        return self.south() or self.west()

    def se(self) -> bool:
        """South or east."""
        return self.south() or self.east()

    def is_full(self) -> bool:
        """Check if every wall is there."""
        return self.east() and self.west() and self.north() and self.south()


class Maze:
    """Maze grid."""

    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int],
        exit: tuple[int, int],
        perfect: bool = False,
        seed: int | None = None,
        output_file_name: str | None = None,
    ) -> None:
        """Maze constructor."""
        self.width: int = width
        self.height: int = height
        self.entry: tuple[int, int] = entry
        self.exit: tuple[int, int] = exit
        self.perfect: bool = perfect
        self.seed: int = seed if seed else random.randint(0, 1_000_000)
        self.output_file_name: str | None = output_file_name
        self._maze: list[list[Cell]] = []
        # init maze full of walls (0xF)
        for y in range(self.height):
            self._maze.append([])
            for x in range(self.width):
                self._maze[y].append(Cell(x, y, 0xF))
        self._generate()

    def __str__(self) -> str:
        """Ascii minimap."""
        grid = self.to_grid()
        minimap: str = ""
        for line in grid:
            for cell in line:
                minimap += '██' if cell else "  "
            minimap += '\n'
        return minimap

    def __repr__(self) -> str:
        """Hex ascii map."""
        ret: str = ""
        for y in range(self.height):
            for x in range(self.width):
                ret += str(self._maze[y][x])
            ret += "\n"
        return ret

    def _generate(self) -> None:
        """Run generation and returns the maze."""
        rng = random.Random(self.seed)
        self._backtracking(rng)

    def _backtracking(self, rng: random.Random) -> None:
        """Iterative backtracking."""
        stack: list[Cell] = []
        visited: set[Cell] = set()
        start = self.get_cell(self.entry[0], self.entry[1])
        stack.append(start)
        visited.add(start)

        while stack:
            current = stack[-1]
            neighbors = self.get_neighbors(current)
            unvisited = [n for n in neighbors if n not in visited]
            rng.shuffle(unvisited)

            if unvisited:
                neighbor = unvisited[0]
                self._open_wall_between(current, neighbor)
                visited.add(neighbor)
                stack.append(neighbor)
            else:
                stack.pop()

    def _open_wall_between(self, cell1: Cell, cell2: Cell) -> None:
        """Open path between two adjacent cells."""
        dx = cell2.x - cell1.x
        dy = cell2.y - cell1.y
        match dx, dy:
            case 1, 0:
                cell1.wall &= ~Wall.EAST.value
                cell2.wall &= ~Wall.WEST.value
            case 0, 1:
                cell1.wall &= ~Wall.SOUTH.value
                cell2.wall &= ~Wall.NORTH.value
            case -1, 0:
                cell1.wall &= ~Wall.WEST.value
                cell2.wall &= ~Wall.EAST.value
            case 0, -1:
                cell1.wall &= ~Wall.NORTH.value
                cell2.wall &= ~Wall.SOUTH.value

    def get_neighbors(self, cell: Cell) -> list[Cell]:
        """Return list of adjacent cells."""
        ret: list[Cell] = []
        for dx, dy in (-1, 0), (1, 0), (0, 1), (0, -1):
            nx, ny = cell.x + dx, cell.y + dy
            if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                continue
            ret.append(self._maze[ny][nx])
        return ret

    def get_cell(self, x: int, y: int) -> Cell:
        """Return cell at (x, y)."""
        return self._maze[y][x]

    def get_maze(self) -> list[list[Cell]]:
        """Return maze rows."""
        return self._maze

    def to_grid(self) -> list[list[bool]]:
        """Convert maze to a 3x-per-cell bool grid."""
        grid: list[list[bool]] = []
        for y, line in enumerate(self.get_maze()):
            # upper 3x3
            grid.append([])
            for cell in line:
                grid[y * 3].append(
                    cell.north() or cell.west()
                    or self.get_cell(cell.x - 1, cell.y).ne()
                    or self.get_cell(cell.x, cell.y - 1).sw()
                )
                grid[y * 3].append(cell.north())
                grid[y * 3].append(
                    cell.north() or cell.east()
                    or self.get_cell(cell.x + 1, cell.y).nw()
                    or self.get_cell(cell.x, cell.y - 1).se()
                )
            # middle 3x3
            grid.append([])
            for cell in line:
                grid[y * 3 + 1].append(cell.west())
                grid[y * 3 + 1].append(cell.is_full())
                grid[y * 3 + 1].append(cell.east())
            # lower 3x3
            grid.append([])
            for cell in line:
                grid[y * 3 + 2].append(
                    cell.south() or cell.west()
                    or self.get_cell(cell.x - 1, cell.y).se()
                    or self.get_cell(cell.x, cell.y + 1).nw()
                )
                grid[y * 3 + 2].append(cell.south())
                grid[y * 3 + 2].append(
                    cell.south() or cell.east()
                    or self.get_cell(cell.x + 1, cell.y).sw()
                    or self.get_cell(cell.x, cell.y + 1).ne()
                )
        return grid
