import time
from display.camera import Camera
from input import KeyboardHandler
from pynput import keyboard
from core import Mode


class Pathfinding:
    def __init__(
        self,
        camera: Camera,
        maze_grid: list[list[bool]],
        solution: list[tuple[int, int]],
        mode: Mode,
    ) -> None:
        self.camera: Camera = camera
        self.maze_grid: list[list[bool]] = maze_grid
        self.solution: list[tuple[int, int]] = solution
        self.keyboard_handler = KeyboardHandler()
        self.keys = mode.keys()

        self.move_speed: float = 2.5
        self.strafe_speed: float = 1.4
        self.rotate_speed: float = 2.0
        self.mouse_sensitivity: float = 0.05

    def closest_cell_to_camera(self) -> tuple[int, int] | None:
        """Returns the closest cell from camera view"""
        cam_x, cam_y = self.camera.pos.x, self.camera.pos.y
        closest = None
        min_dist = float("inf")
        for x, y in self.solution:
            dist = abs(x - cam_x) + abs(y - cam_y)
            if dist < min_dist:
                min_dist = dist
                closest = (x, y)
        return closest

    def _pathfinding(self) -> list[tuple[keyboard.Key, float]]:
        """Generates sequence to walk to the exit cell"""
        start_cell = self.closest_cell_to_camera()
        if start_cell is None:
            return []

        try:
            start_idx = self.solution.index(start_cell)
        except ValueError:
            start_idx = 0
        ordered_path = self.solution[start_idx:]

        moves: list[tuple[keyboard.Key, float]] = []

        for i in range(len(ordered_path) - 1):
            x1, y1 = ordered_path[i]
            x2, y2 = ordered_path[i + 1]
            dx = x2 - x1
            dy = y2 - y1

            if dx != 0:
                key = keyboard.Key.right if dx > 0 else keyboard.Key.left
                distance = abs(dx)
            elif dy != 0:
                key = self.keys.forward if dy > 0 else self.keys.back
                distance = abs(dy)
            else:
                continue

            duration = distance / self.move_speed
            moves.append((key, duration))

        return moves

    def play_solution(self) -> None:
        """Play the pathfinding sequence"""
        path = self._pathfinding()
        for key, duration in path:
            self.keyboard_handler.keys_pressed.add(key)
            time.sleep(duration)
            self.keyboard_handler.keys_pressed.discard(key)
