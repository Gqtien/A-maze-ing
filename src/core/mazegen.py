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
        self.wall: int = walls
        self.x: int = x
        self.y: int = y

    def __repr__(self) -> str:
        return hex(self.wall)[2:].upper()


class Maze:
    """Maze grid."""
    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int],
        exit: tuple[int, int],
        perfect: bool,
        seed: int | None,
        output_file_name: str | None = None,
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.entry: tuple[int, int] = entry
        self.exit: tuple[int, int] = exit
        self.perfect: bool = perfect
        self.seed: int | None = seed
        self.output_file_name: str | None = output_file_name
        self._maze: list[list[Cell]] = []
        for y in range(self.height):
            self._maze.append([])
            for x in range(self.width):
                self._maze[y].append(Cell(x, y, 15))

    def __str__(self) -> str:
        ret: str = ""
        for y in range(self.height):
            for x in range(self.width):
                ret += str(self._maze[y][x])
            ret += "\n"
        return ret

    def get_neighbors(self, cell: Cell) -> list[Cell]:
        """Returns list of adjacent cells."""
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

    def rows(self) -> list[list[Cell]]:
        """Return maze rows (read-only view)."""
        return self._maze


class MazeGenerator:
    """Generates mazes."""
    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int],
        exit: tuple[int, int],
        perfect: bool = True,
        seed: int | None = None,
        output_file_name: str | None = None,
    ) -> None:
        self._maze = Maze(
            width=width,
            height=height,
            seed=seed,
            entry=entry,
            exit=exit,
            perfect=perfect,
            output_file_name=output_file_name,
        )

    def generate(self) -> Maze:
        """Runs generation and returns the maze."""
        rng = random.Random(self._maze.seed if self._maze.seed else random.seed())
        self._generate_from(self._maze.entry[0], self._maze.entry[1], rng)
        return self._maze

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

    def _generate_from(
        self,
        x: int,
        y: int,
        rng: random.Random,
        visited: list[Cell] = [],
    ) -> None:
        """Recursive backtracking."""
        maze = self._maze
        current = maze.get_cell(x, y)
        visited.append(current)
        neighbors = maze.get_neighbors(current)
        rng.shuffle(neighbors)
        for neighbor in neighbors:
            if neighbor in visited:
                continue
            self._open_wall_between(current, neighbor)
            self._generate_from(neighbor.x, neighbor.y, rng, visited)
