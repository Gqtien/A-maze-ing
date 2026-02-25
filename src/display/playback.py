import time
import math
import threading
from typing import TypeAlias
from display.camera import Camera


GridCell: TypeAlias = tuple[int, int]
WorldPoint: TypeAlias = tuple[float, float]
GridStep: TypeAlias = tuple[int, int]
Segment: TypeAlias = tuple[WorldPoint, WorldPoint, GridStep]
Segments: TypeAlias = list[Segment]


class Playback:
    """Playback for the camera to follow the solution."""

    def __init__(
        self,
        camera: Camera,
        solution: list[GridCell]
    ) -> None:
        """Initialize the playback."""
        self.camera: Camera = camera
        self.solution: list[GridCell] = solution
        self.tick: float = 0.002
        self.speed: float = 10
        self.is_playing: bool = False
        self._stop = threading.Event()

    def stop(self) -> None:
        """Stop the playback."""
        self._stop.set()

    def _closest_cell_index(self) -> int:
        """Return the index of the closest cell in the solution."""
        camera_x, camera_y = self.camera.pos.x, self.camera.pos.y
        best_index = 0
        best_distance = float("inf")
        for index, (cell_x, cell_y) in enumerate(self.solution):
            distance = abs(cell_x - camera_x) + abs(cell_y - camera_y)
            if distance < best_distance:
                best_distance = distance
                best_index = index
        return best_index

    @staticmethod
    def _cell_center(cell: GridCell) -> WorldPoint:
        """Return the center of a cell."""
        return (cell[0] + 0.5, cell[1] + 0.5)

    def _build_segments(self) -> Segments:
        """Combine same direction steps into straight segments."""
        start_cell_index = self._closest_cell_index()
        cells = self.solution[start_cell_index:]
        if len(cells) < 2:
            return []

        segments: Segments = []
        segment_start_cell: GridCell = cells[0]
        current_step: GridStep = (
            cells[1][0] - cells[0][0],
            cells[1][1] - cells[0][1],
        )

        for i in range(1, len(cells) - 1):
            next_step: GridStep = (
                cells[i + 1][0] - cells[i][0],
                cells[i + 1][1] - cells[i][1],
            )
            if next_step != current_step:
                segments.append((
                    self._cell_center(segment_start_cell),
                    self._cell_center(cells[i]),
                    current_step,
                ))
                segment_start_cell = cells[i]
                current_step = next_step

        segments.append((
            self._cell_center(segment_start_cell),
            self._cell_center(cells[-1]),
            current_step,
        ))
        return segments

    @staticmethod
    def _smoothstep(t: float) -> float:
        """Return a smooth step function."""
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _shortest_angle(
        a: tuple[float, float],
        b: tuple[float, float],
    ) -> float:
        """Return the shortest angle between two vectors."""
        return (
            (math.atan2(b[1], b[0]) - math.atan2(a[1], a[0]) + math.pi)
            % (2 * math.pi)
            - math.pi
        )

    def _ease_to(self, x: float, y: float, duration: float) -> None:
        """Ease the camera to a position."""
        start_x, start_y = self.camera.pos.x, self.camera.pos.y
        dx, dy = x - start_x, y - start_y
        if abs(dx) + abs(dy) < 1e-9 or duration <= 0.0:
            self.camera.pos.x = x
            self.camera.pos.y = y
            return

        start_time = time.perf_counter()
        while not self._stop.is_set():
            elapsed = time.perf_counter() - start_time
            if elapsed >= duration:
                break
            t = self._smoothstep(elapsed / duration)
            self.camera.pos.x = start_x + dx * t
            self.camera.pos.y = start_y + dy * t
            time.sleep(self.tick)

        if not self._stop.is_set():
            self.camera.pos.x = x
            self.camera.pos.y = y

    def _rotate(self, angle: float, duration: float) -> None:
        """Rotate the camera to an angle."""
        if abs(angle) < 1e-6:
            return
        start_time = time.perf_counter()
        progress_applied = 0.0
        while not self._stop.is_set():
            elapsed = time.perf_counter() - start_time
            if elapsed >= duration:
                break
            t = self._smoothstep(elapsed / duration)
            # Only apply the delta since the last frame to avoid over rotating
            self.camera.direction.rotate(angle * (t - progress_applied))
            progress_applied = t
            time.sleep(self.tick)
        if not self._stop.is_set():
            self.camera.direction.rotate(angle * (1.0 - progress_applied))

    def play_solution(self) -> None:
        """Play the solution."""
        if self.is_playing:
            self._stop.set()
            self.is_playing = not self.is_playing
            return
        self.is_playing = True
        self._stop.clear()

        try:
            segments: Segments = self._build_segments()
            if not segments:
                return

            self._ease_to(segments[0][0][0], segments[0][0][1], 0.08)
            if self._stop.is_set():
                return

            camera_dir: tuple[float, float] = (
                self.camera.direction.x,
                self.camera.direction.y,
            )
            self._rotate(self._shortest_angle(camera_dir, segments[0][2]), 0.2)
            if self._stop.is_set():
                return

            for segment_index, (start, end, step) in enumerate(segments):
                start_x, start_y = start
                end_x, end_y = end

                distance = math.hypot(end_x - start_x, end_y - start_y)
                duration = distance / self.speed

                turn_angle = 0.0
                if segment_index + 1 < len(segments):
                    turn_angle = self._shortest_angle(
                        step,
                        segments[segment_index + 1][2],
                    )

                has_turn = abs(turn_angle) > 1e-3
                turn_blend_duration = (
                    min(0.15, duration * 0.45)
                    if has_turn else
                    0.0
                )
                turn_blend_start_t = duration - turn_blend_duration
                turn_progress = 0.0

                # Begin turning before the end of the segment
                # to avoid stopping and turning again
                start_time = time.perf_counter()
                while not self._stop.is_set():
                    elapsed = time.perf_counter() - start_time
                    if elapsed >= duration:
                        break

                    t = elapsed / duration if duration > 0.0 else 1.0
                    self.camera.pos.x = start_x + (end_x - start_x) * t
                    self.camera.pos.y = start_y + (end_y - start_y) * t

                    if (
                        has_turn
                        and elapsed >= turn_blend_start_t
                        and turn_blend_duration > 0.0
                    ):
                        rot_t = self._smoothstep(
                            (elapsed - turn_blend_start_t)
                            / turn_blend_duration,
                        )
                        self.camera.direction.rotate(
                            turn_angle * (rot_t - turn_progress),
                        )
                        turn_progress = rot_t

                    time.sleep(self.tick)

                if self._stop.is_set():
                    return

                self.camera.pos.x = end_x
                self.camera.pos.y = end_y

                if has_turn and turn_progress < 0.99:
                    self._rotate(turn_angle * (1.0 - turn_progress), 0.03)
        finally:
            self.is_playing = False
