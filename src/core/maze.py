import random
from enum import Enum
from typing import Optional
from assets import DIGITS
from core.config import Pattern


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
        entry_pos: tuple[int, int],
        exit_pos: tuple[int, int],
        perfect: bool,
        output_file_name: str,
        seed: int | None = None,
        pattern: Pattern | None = None,
        algo: str | None = None,
    ) -> None:
        """Maze constructor."""
        self.width: int = width
        self.height: int = height
        self.entry_pos: tuple[int, int] = entry_pos
        self.exit_pos: tuple[int, int] = exit_pos
        self.perfect: bool = bool(perfect)
        self._maze: list[list[Cell]] = []
        self.pattern: Pattern = pattern if pattern else Pattern("42")
        self.algo: str = (algo or "backtracking").lower()
        self.seed: int = (
            seed
            if seed is not None
            else random.randint(0, 1_000_000)
        )

        self.pattern_cells: set[Cell] = set()
        self._generate()
        self.solution = self.solve()

        if output_file_name is not None:
            self.save_to_file(output_file_name)

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
        """
            Hex ascii map,
            entry and exit positions,
            shortest valid path from entry to exit.
        """
        ret: str = ""
        for y in range(self.height):
            for x in range(self.width):
                ret += repr(self._maze[y][x])
            ret += "\n"
        ret += "\n"

        for pos in (self.entry_pos, self.exit_pos):
            ret += ",".join(map(str, pos)) + "\n"

        ret += self.cardinal_path(self.solution)
        ret += "\n"
        return ret

    def _generate(self) -> None:
        """Run generation and returns the maze."""
        # NOTE: init maze full of walls (0xF)
        for y in range(self.height):
            row: list[Cell] = []
            for x in range(self.width):
                row.append(Cell(x, y, 0xF))
            self._maze.append(row)

        rng = random.Random(self.seed)

        match self.algo:
            case "prim":
                self._prim(rng)
            case _:
                self._backtracking(rng)

        if not self.perfect:
            self._add_exit_loop(rng)

    def get_pattern_cells(self) -> set[Cell]:
        """Return cells to mark the 42 in the center."""
        d = self.pattern.digits()
        pattern_first: list[str] = DIGITS[d.first]
        pattern_second: list[str] = DIGITS[d.second]

        digit_height: int = len(pattern_first)
        digit_width: int = len(pattern_first[0]) if pattern_first else 0
        total_width: int = digit_width * 2 + 1

        if self.width < total_width or self.height < digit_height:
            print("Error: Maze is too small to fit the pattern in its center.")
            return set()

        top: int = (self.height - digit_height) // 2
        left_first: int = (self.width - total_width) // 2
        left_second: int = left_first + digit_width + 1

        cells: set[Cell] = set()

        for pattern, left in (
            (pattern_first, left_first),
            (pattern_second, left_second),
        ):
            for dy, row in enumerate(pattern):
                for dx, ch in enumerate(row):
                    if ch != "O":
                        continue
                    x: int = left + dx
                    y: int = top + dy
                    if (x, y) == self.entry_pos or (x, y) == self.exit_pos:
                        continue
                    cells.add(self.get_cell(x, y))

        return cells

    def _backtracking(self, rng: random.Random) -> None:
        """Perfect maze via iterative backtracking."""
        stack: list[Cell] = []
        self.pattern_cells = self.get_pattern_cells()
        visited: set[Cell] = set(self.pattern_cells)
        start: Cell = self.get_cell(*self.entry_pos)
        stack.append(start)
        visited.add(start)

        while stack:
            current: Cell = stack[-1]
            neighbors: list[Cell] = self.get_neighbors(current)
            unvisited: list[Cell] = [n for n in neighbors if n not in visited]
            rng.shuffle(unvisited)

            if unvisited:
                neighbor: Cell = unvisited[0]
                self._open_wall_between(current, neighbor)
                visited.add(neighbor)
                stack.append(neighbor)
            else:
                stack.pop()

    def _prim(self, rng: random.Random) -> None:
        """Perfect maze via Prim's algorithm."""
        self.pattern_cells = self.get_pattern_cells()
        in_maze: set[Cell] = set(self.pattern_cells)
        start: Cell = self.get_cell(*self.entry_pos)
        in_maze.add(start)

        frontier: list[tuple[Cell, Cell]] = []
        for neighbor in self.get_neighbors(start):
            if neighbor not in in_maze:
                frontier.append((start, neighbor))

        while frontier:
            cell_in, cell_out = frontier.pop(rng.randint(0, len(frontier) - 1))
            if cell_out in in_maze:
                continue
            self._open_wall_between(cell_in, cell_out)
            in_maze.add(cell_out)
            for neighbor in self.get_neighbors(cell_out):
                if neighbor not in in_maze:
                    frontier.append((cell_out, neighbor))

    def solve(self) -> list[Cell]:
        """Dijkstra's algo."""
        rows, cols = len(self._maze), len(self._maze[0])

        distances = [[float('inf')] * cols for _ in range(rows)]
        parents: list[list[Optional[tuple[int, int]]]] = (
            [[None] * cols for _ in range(rows)]
        )
        visited = [[False] * cols for _ in range(rows)]

        start_x, start_y = self.entry_pos
        exit_x, exit_y = self.exit_pos
        distances[start_y][start_x] = 0

        while True:
            min_dist = float('inf')
            current: Optional[tuple[int, int]] = None
            for y in range(rows):
                for x in range(cols):
                    if not visited[y][x] and distances[y][x] < min_dist:
                        min_dist = distances[y][x]
                        current = (x, y)

            if current is None:
                break

            x, y = current
            visited[y][x] = True

            if (x, y) == (exit_x, exit_y):
                path: list[Cell] = []
                while (x, y) != (start_x, start_y):
                    path.append(self.get_cell(x, y))
                    parent = parents[y][x]
                    assert parent is not None
                    x, y = parent
                path.append(self.get_cell(start_x, start_y))
                path.reverse()
                return path

            for neighbor in self.get_accessible_neighbors(self.get_cell(x, y)):
                nx, ny = neighbor.x, neighbor.y
                if not visited[ny][nx]:
                    if distances[ny][nx] > distances[y][x] + 1:
                        distances[ny][nx] = distances[y][x] + 1
                        parents[ny][nx] = (x, y)

        return []

    def cardinal_path(self, path: list[Cell]) -> str:
        """Convert cells path to cardinal path."""
        if not path:
            return ""

        direction: str = ""
        previous = path[0]

        for cell in path[1:]:
            dx = cell.x - previous.x
            dy = cell.y - previous.y

            if dx == 1 and dy == 0:
                direction += "E"
            elif dx == -1 and dy == 0:
                direction += "W"
            elif dx == 0 and dy == -1:
                direction += "N"
            elif dx == 0 and dy == 1:
                direction += "S"
            else:
                raise ValueError(f"Invalid path between {previous} and {cell}")

            previous = cell

        return direction

    def _degree(self, c: Cell) -> int:
        """Number of open sides."""
        return (
            int(not c.north())
            + int(not c.east())
            + int(not c.south())
            + int(not c.west())
        )

    def _is_open_between(self, a: Cell, b: Cell) -> bool:
        """
            True if there is already an opening between adjacent cells a and b.
        """
        dx, dy = b.x - a.x, b.y - a.y
        match dx, dy:
            case 1, 0:
                return (
                    (a.wall & Wall.EAST.value) == 0
                    and (b.wall & Wall.WEST.value) == 0
                )
            case -1, 0:
                return (
                    (a.wall & Wall.WEST.value) == 0
                    and (b.wall & Wall.EAST.value) == 0
                )
            case 0, 1:
                return (
                    (a.wall & Wall.SOUTH.value) == 0
                    and (b.wall & Wall.NORTH.value) == 0
                )
            case 0, -1:
                return (
                    (a.wall & Wall.NORTH.value) == 0
                    and (b.wall & Wall.SOUTH.value) == 0
                )
        return False

    def _add_exit_loop(self, rng: random.Random) -> None:
        """Add one shortcut from the exit."""
        exit_cell = self.get_cell(*self.exit_pos)
        blocked = self.pattern_cells
        cur, prev = exit_cell, None

        for _ in range(self.width * self.height):
            neighbors = [
                n for n in self.get_neighbors(cur)
                if n not in blocked and n != prev
            ]
            rng.shuffle(neighbors)
            if not neighbors:
                break
            nxt = neighbors[0]
            if not self._is_open_between(cur, nxt):
                self._open_wall_between(cur, nxt)
            prev, cur = cur, nxt
            if self._degree(cur) >= 2:
                return

        candidates = [
            n for n in self.get_neighbors(exit_cell)
            if n not in blocked and not self._is_open_between(exit_cell, n)
        ]
        if candidates:
            self._open_wall_between(exit_cell, rng.choice(candidates))

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

    def get_accessible_neighbors(self, cell: Cell) -> list[Cell]:
        neighbors = []
        x, y = cell.x, cell.y
        if not cell.wall & 0x1:  # North
            neighbors.append(self.get_cell(x, y-1))
        if not cell.wall & 0x2:  # East
            neighbors.append(self.get_cell(x+1, y))
        if not cell.wall & 0x4:  # South
            neighbors.append(self.get_cell(x, y+1))
        if not cell.wall & 0x8:  # West
            neighbors.append(self.get_cell(x-1, y))
        return neighbors

    def get_cell(self, x: int, y: int) -> Cell:
        """Return cell at (x, y)."""
        return self._maze[y][x]

    def get_maze(self) -> list[list[Cell]]:
        """Return maze rows."""
        return self._maze

    def to_grid(self) -> list[list[bool]]:
        """Convert maze to a bool grid."""
        gw = self.width * 2 + 1
        gh = self.height * 2 + 1

        # start full of walls
        grid: list[list[bool]] = [[True] * gw for _ in range(gh)]

        for y in range(self.height):
            for x in range(self.width):
                cell = self.get_cell(x, y)

                cx = 2 * x + 1
                cy = 2 * y + 1

                # cell center is always a path
                grid[cy][cx] = False

                # open passages according to missing walls
                if not cell.north():
                    grid[cy - 1][cx] = False
                if not cell.south():
                    grid[cy + 1][cx] = False
                if not cell.west():
                    grid[cy][cx - 1] = False
                if not cell.east():
                    grid[cy][cx + 1] = False

        return grid

    def solution_to_grid(self) -> list[tuple[int, int]]:
        solution_grid = []
        for cell, next_cell in zip(self.solution, self.solution[1:]):
            cx, cy = 2 * cell.x + 1, 2 * cell.y + 1
            nx, ny = 2 * next_cell.x + 1, 2 * next_cell.y + 1

            solution_grid.append((cx, cy))
            mx, my = (cx + nx) // 2, (cy + ny) // 2
            solution_grid.append((mx, my))
        last = self.solution[-1]
        solution_grid.append((2*last.x + 1, 2*last.y + 1))

        return solution_grid

    def pattern_core_to_grid(self) -> list[tuple[int, int]]:
        """Return grid coords of pattern cells and links only (no outline)."""
        pattern_cells = self.pattern_cells
        out: list[tuple[int, int]] = []
        for c in pattern_cells:
            out.append((2 * c.x + 1, 2 * c.y + 1))
            for n in self.get_neighbors(c):
                if n in pattern_cells:
                    out.append((c.x + n.x + 1, c.y + n.y + 1))
        return out

    def pattern_to_grid(self) -> list[tuple[int, int]]:
        """Return grid coords of pattern cells, links, and 1 cell border."""
        out = self.pattern_core_to_grid()
        gw, gh = 2 * self.width + 1, 2 * self.height + 1
        for (gx, gy) in list(out):
            for dgx, dgy in (
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (-1, 1), (1, -1), (-1, -1),
            ):
                ngx, ngy = gx + dgx, gy + dgy
                if 0 <= ngx < gw and 0 <= ngy < gh:
                    out.append((ngx, ngy))
        return out

    def save_to_file(self, filename: str) -> None:
        """Save the hex representation of the maze to file."""
        try:
            with open(filename, "w") as file:
                file.write(repr(self))
        except Exception as e:
            print(f"Error while trying to save maze to {filename}: {e}")
