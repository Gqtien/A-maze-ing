from random import randint, Random
from enum import Enum
from assets import DIGITS
from core.config import Pattern, Algo


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

    def is_full(self) -> bool:
        """Check if every wall is there."""
        return self.east() and self.west() and self.north() and self.south()


class Maze:
    """Maze grid.

    TODO:
    You must provide a short documentation describing how to:
    • Instantiate and use your generator, with at least a basic example.
    • Pass custom parameters (e.g., size, seed).
    • Access the generated structure, and access at least a solution.
    • The main README.md file (not part of the reusable module)
     must also contain this short documentation.

    NOTE: check readme requierments

    """

    def __init__(
        self,
        width: int,
        height: int,
        entry_pos: tuple[int, int],
        exit_pos: tuple[int, int],
        output_file_name: str | None = None,
        perfect: bool = True,
        seed: int | None = None,
        pattern: Pattern | None = None,
        algo: Algo = Algo.BACKTRACKING,
    ) -> None:
        """Maze constructor."""
        self.width: int = width
        self.height: int = height
        self.entry_pos: tuple[int, int] = entry_pos
        self.exit_pos: tuple[int, int] = exit_pos
        self.perfect: bool = perfect
        self._maze: list[list[Cell]] = []
        self.pattern: Pattern = pattern if pattern else Pattern("42")
        self.algo: Algo = algo
        self.seed: int = seed if seed is not None else randint(0, int(1e9))

        self.pattern_cells: set[Cell] = set()
        self._generate()
        self.solution: list[Cell] = self.pathfind(entry_pos, exit_pos)

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
        """Hex ascii map.

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

        rng = Random(self.seed)

        match self.algo:
            case Algo.PRIM:
                self._prim(rng)
            case Algo.BACKTRACKING:
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
            raise ValueError(
                f"Maze too small for pattern: got {self.width}x{self.height}, "
                f"needs at least {total_width}x{digit_height}"
            )

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

    def _backtracking(self, rng: Random) -> None:
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

    def _prim(self, rng: Random) -> None:
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

    def pathfind(self, a: tuple[int, int], b: tuple[int, int]) -> list[Cell]:
        """Dijkstra's algo."""
        if not self._maze or not self._maze[0]:
            return []
        rows, cols = len(self._maze), len(self._maze[0])

        distances = [[float('inf')] * cols for _ in range(rows)]
        parents: list[list[tuple[int, int] | None]] = [
            [None] * cols for _ in range(rows)
        ]
        visited = [[False] * cols for _ in range(rows)]

        start_x, start_y = a
        exit_x, exit_y = b
        distances[start_y][start_x] = 0

        while True:
            min_dist = float('inf')
            current: tuple[int, int] | None = None
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
                    if parent is None:
                        return []
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
        """Return true if there is an opening between a and b.

        assumes a and b are adjacent.
        """
        dx, dy = b.x - a.x, b.y - a.y
        match dx, dy:
            case 1, 0:
                return (
                    (a.wall & Wall.EAST.value) == 0 and
                    (b.wall & Wall.WEST.value) == 0
                )
            case -1, 0:
                return (
                    (a.wall & Wall.WEST.value) == 0 and
                    (b.wall & Wall.EAST.value) == 0
                )
            case 0, 1:
                return (
                    (a.wall & Wall.SOUTH.value) == 0 and
                    (b.wall & Wall.NORTH.value) == 0
                )
            case 0, -1:
                return (
                    (a.wall & Wall.NORTH.value) == 0 and
                    (b.wall & Wall.SOUTH.value) == 0
                )
        return False

    def _add_exit_loop(self, rng: Random) -> None:
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
        """Return a list of accessible adjacent cells."""
        neighbors: list[Cell] = []
        x, y = cell.x, cell.y
        if not (cell.wall & 0x1) and y > 0:  # North
            neighbors.append(self._maze[y - 1][x])
        if not (cell.wall & 0x2) and x + 1 < self.width:  # East
            neighbors.append(self._maze[y][x + 1])
        if not (cell.wall & 0x4) and y + 1 < self.height:  # South
            neighbors.append(self._maze[y + 1][x])
        if not (cell.wall & 0x8) and x > 0:  # West
            neighbors.append(self._maze[y][x - 1])
        return neighbors

    def get_cell(self, x: int, y: int) -> Cell:
        """Return cell at (x, y)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(
                f"Cell ({x}, {y}) out of bounds for "
                f"{self.width}x{self.height}"
            )
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
        """Convert a list of Cell to a grid tracing solution path."""
        solution_grid = []
        for cell, next_cell in zip(self.solution, self.solution[1:]):
            cx, cy = 2 * cell.x + 1, 2 * cell.y + 1
            nx, ny = 2 * next_cell.x + 1, 2 * next_cell.y + 1

            solution_grid.append((cx, cy))
            mx, my = (cx + nx) // 2, (cy + ny) // 2
            solution_grid.append((mx, my))
        if not self.solution:
            return []
        last = self.solution[-1]
        solution_grid.append((2 * last.x + 1, 2 * last.y + 1))

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
        with open(filename, "w", encoding="utf-8") as file:
            file.write(repr(self))
