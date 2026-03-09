import math
from enum import Enum, auto
from typing import TypeAlias
from display.camera import Camera


GridCell: TypeAlias = tuple[int, int]
WorldPoint: TypeAlias = tuple[float, float]
GridStep: TypeAlias = tuple[int, int]
Segment: TypeAlias = tuple[WorldPoint, WorldPoint, GridStep]
Segments: TypeAlias = list[Segment]


class Phase(Enum):
    """States of the playback."""

    IDLE = auto()
    EASE_TO_START = auto()
    ROTATE_INITIAL = auto()
    WALK = auto()
    ROTATE_TURN = auto()


class Playback:
    """Playback for the camera to follow the solution."""

    def __init__(
        self,
        camera: Camera,
        solution: list[GridCell],
    ) -> None:
        """Initialize the playback."""
        self.camera: Camera = camera
        self.solution: list[GridCell] = solution
        self.speed: float = 2.5
        self.is_playing: bool = False

        self._phase: Phase = Phase.IDLE
        self._segments: Segments = []
        self._seg_idx: int = 0

        # ease_to state
        self._ease_start: WorldPoint = (0.0, 0.0)
        self._ease_end: WorldPoint = (0.0, 0.0)
        self._ease_elapsed: float = 0.0
        self._ease_duration: float = 0.0

        # rotate state
        self._rot_angle: float = 0.0
        self._rot_elapsed: float = 0.0
        self._rot_duration: float = 0.0
        self._rot_progress: float = 0.0

        # walk state
        self._walk_start: WorldPoint = (0.0, 0.0)
        self._walk_end: WorldPoint = (0.0, 0.0)
        self._walk_elapsed: float = 0.0
        self._walk_duration: float = 0.0
        self._walk_turn_angle: float = 0.0
        self._walk_turn_blend_duration: float = 0.0
        self._walk_turn_blend_start_t: float = 0.0
        self._walk_turn_progress: float = 0.0

    def play_solution(self) -> None:
        """Start (or stop if already playing) the playback."""
        if self.is_playing:
            self.stop()
            return

        segments = self._build_segments()
        if not segments:
            return

        self.is_playing = True
        self._segments = segments
        self._seg_idx = 0
        self._start_ease_to(segments[0][0], 0.08)

    def stop(self) -> None:
        """Stop the playback immediately."""
        self.is_playing = False
        self._phase = Phase.IDLE

    def update(self, dt: float) -> None:
        """Advance the playback by dt."""
        if not self.is_playing:
            return

        if self._phase == Phase.EASE_TO_START:
            self._update_ease(dt)
        elif self._phase == Phase.ROTATE_INITIAL:
            self._update_rotate(dt)
        elif self._phase == Phase.WALK:
            self._update_walk(dt)
        elif self._phase == Phase.ROTATE_TURN:
            self._update_rotate(dt)

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
        """Return a smooth step."""
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

    def _start_ease_to(self, target: WorldPoint, duration: float) -> None:
        self._ease_start = (self.camera.pos.x, self.camera.pos.y)
        self._ease_end = target
        self._ease_elapsed = 0.0
        self._ease_duration = duration
        self._phase = Phase.EASE_TO_START

    def _start_rotate(
        self,
        angle: float,
        duration: float,
        phase: Phase,
    ) -> None:
        self._rot_angle = angle
        self._rot_elapsed = 0.0
        self._rot_duration = duration
        self._rot_progress = 0.0
        self._phase = phase

    def _start_walk(self, seg_idx: int) -> None:
        start, end, step = self._segments[seg_idx]
        distance = math.hypot(end[0] - start[0], end[1] - start[1])
        duration = distance / self.speed

        turn_angle = 0.0
        if seg_idx + 1 < len(self._segments):
            turn_angle = self._shortest_angle(
                step,
                self._segments[seg_idx + 1][2],
            )

        has_turn = abs(turn_angle) > 1e-3
        turn_blend_duration = min(0.15, duration * 0.45) if has_turn else 0.0

        self._walk_start = start
        self._walk_end = end
        self._walk_elapsed = 0.0
        self._walk_duration = duration
        self._walk_turn_angle = turn_angle
        self._walk_turn_blend_duration = turn_blend_duration
        self._walk_turn_blend_start_t = duration - turn_blend_duration
        self._walk_turn_progress = 0.0
        self._phase = Phase.WALK

    def _update_ease(self, dt: float) -> None:
        sx, sy = self._ease_start
        ex, ey = self._ease_end

        self._ease_elapsed += dt
        if (
            self._ease_elapsed >= self._ease_duration
            or self._ease_duration <= 0.0
        ):
            self.camera.pos.x = ex
            self.camera.pos.y = ey
            # rotate to face the first segment
            camera_dir = (self.camera.direction.x, self.camera.direction.y)
            angle = self._shortest_angle(camera_dir, self._segments[0][2])
            self._start_rotate(angle, 0.2, Phase.ROTATE_INITIAL)
            return

        t = self._smoothstep(self._ease_elapsed / self._ease_duration)
        self.camera.pos.x = sx + (ex - sx) * t
        self.camera.pos.y = sy + (ey - sy) * t

    def _update_rotate(self, dt: float) -> None:
        self._rot_elapsed += dt

        if (
            self._rot_elapsed >= self._rot_duration
            or self._rot_duration <= 0.0
        ):
            remaining = self._rot_angle * (1.0 - self._rot_progress)
            if abs(remaining) > 1e-9:
                self.camera.direction.rotate(remaining)
            self._start_walk(self._seg_idx)
            return

        t = self._smoothstep(self._rot_elapsed / self._rot_duration)
        self.camera.direction.rotate(
            self._rot_angle * (t - self._rot_progress),
        )
        self._rot_progress = t

    def _update_walk(self, dt: float) -> None:
        sx, sy = self._walk_start
        ex, ey = self._walk_end

        self._walk_elapsed += dt
        elapsed = self._walk_elapsed
        duration = self._walk_duration

        if elapsed >= duration:
            self.camera.pos.x = ex
            self.camera.pos.y = ey
            self._on_walk_done()
            return

        t = elapsed / duration if duration > 0.0 else 1.0
        self.camera.pos.x = sx + (ex - sx) * t
        self.camera.pos.y = sy + (ey - sy) * t

        # blend turn near the end of the segment
        if (
            abs(self._walk_turn_angle) > 1e-3
            and elapsed >= self._walk_turn_blend_start_t
            and self._walk_turn_blend_duration > 0.0
        ):
            rot_t = self._smoothstep(
                (elapsed - self._walk_turn_blend_start_t)
                / self._walk_turn_blend_duration
            )
            self.camera.direction.rotate(
                self._walk_turn_angle * (rot_t - self._walk_turn_progress)
            )
            self._walk_turn_progress = rot_t

    def _on_walk_done(self) -> None:
        remaining_turn = (
            self._walk_turn_angle * (1.0 - self._walk_turn_progress)
        )
        self._seg_idx += 1

        if self._seg_idx >= len(self._segments):
            if abs(remaining_turn) > 1e-3:
                self.camera.direction.rotate(remaining_turn)
            self.stop()
            return

        if self._walk_turn_progress < 0.99 and abs(remaining_turn) > 1e-3:
            self._start_rotate(remaining_turn, 0.03, Phase.ROTATE_TURN)
        else:
            self._start_walk(self._seg_idx)
