import math
from utils.geometry import Vec2, Rect
from input.keyboard import keys_pressed
from pynput import keyboard


def face_open_corridor(grid: list[list[bool]], pos: Vec2) -> Vec2:
    """First cardinal (E/W/N/S) from pos that points to a non-wall cell."""
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = int(pos.x + dx), int(pos.y + dy)
        if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]) and not grid[ny][nx]:
            return Vec2(dx, dy)
    return Vec2(1, 0)


class Camera:
    """First-person camera."""

    def __init__(
        self,
        pos: Vec2,
        direction: Vec2,
        fov: int,
        grid: list[list[bool]],
        mode: str = "wasd"
    ) -> None:
        """Pos and direction in grid coords, FOV in degrees."""
        self.pos: Vec2 = pos
        self.direction: Vec2 = direction
        self.fov: int = fov
        self.fov_scale = math.tan(math.radians(self.fov) / 2)
        self.grid: list[list[bool]] = grid
        self.grid_width: int = len(grid[0]) if grid else 0
        self.grid_height: int = len(grid) if grid else 0
        self.mode: str = mode.lower()

        # Movement in units per second (independant from frame rate)
        self.move_speed: float = 2.5
        self.strafe_speed: float = 1.4
        self.rotate_speed: float = 2.0
        self.fov_change_speed: float = 30.0

    def _can_move_to(self, new_x: float, new_y: float) -> bool:
        """Check if the new position is not in a wall."""
        map_x: int = int(new_x)
        map_y: int = int(new_y)

        if (
            map_x < 0
            or map_y < 0
            or map_x >= self.grid_width
            or map_y >= self.grid_height
        ):
            return False

        return not self.grid[map_y][map_x]

    def _try_move_with_slide(self, new_x: float, new_y: float) -> None:
        """Try to move to new position, sliding along walls if blocked."""
        if self._can_move_to(new_x, new_y):
            self.pos.x = new_x
            self.pos.y = new_y
        else:
            if self._can_move_to(new_x, self.pos.y):
                self.pos.x = new_x
            elif self._can_move_to(self.pos.x, new_y):
                self.pos.y = new_y

    def move(self, delta_time_ns: int) -> None:
        """Move the camera."""
        dt: float = delta_time_ns / 1000000000.0

        if keyboard.Key.right in keys_pressed:
            self.direction.rotate(self.rotate_speed * dt)
        elif keyboard.Key.left in keys_pressed:
            self.direction.rotate(-self.rotate_speed * dt)

        if keyboard.Key.up in keys_pressed:
            new_fov = self.fov + self.fov_change_speed * dt
            self.fov = min(120, int(new_fov))
            self.fov_scale = math.tan(math.radians(self.fov) / 2)
        elif keyboard.Key.down in keys_pressed:
            new_fov = self.fov - self.fov_change_speed * dt
            self.fov = max(30, int(new_fov))
            self.fov_scale = math.tan(math.radians(self.fov) / 2)

        if self.mode[0] in keys_pressed:
            new_x = self.pos.x + self.direction.x * self.move_speed * dt
            new_y = self.pos.y + self.direction.y * self.move_speed * dt
            self._try_move_with_slide(new_x, new_y)
        elif self.mode[2] in keys_pressed:
            new_x = self.pos.x - self.direction.x * self.move_speed * dt
            new_y = self.pos.y - self.direction.y * self.move_speed * dt
            self._try_move_with_slide(new_x, new_y)

        if self.mode[1] in keys_pressed:
            new_x = self.pos.x + self.direction.y * self.strafe_speed * dt
            new_y = self.pos.y - self.direction.x * self.strafe_speed * dt
            self._try_move_with_slide(new_x, new_y)
        elif self.mode[3] in keys_pressed:
            new_x = self.pos.x - self.direction.y * self.strafe_speed * dt
            new_y = self.pos.y + self.direction.x * self.strafe_speed * dt
            self._try_move_with_slide(new_x, new_y)

    def get_rect(self, size: int) -> Rect:
        """Get a rect from the camera pos."""
        return Rect(
            int(self.pos.x * size) - size // 4,
            int(self.pos.y * size) - size // 4,
            size // 2,
            size // 2
        )
