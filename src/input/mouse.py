import threading
from pynput.mouse import Listener, Controller
from core import env_int


class MouseHandler:
    _instance: "MouseHandler | None" = None

    def __new__(cls) -> "MouseHandler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.hook = False
        self.mouse: Controller | None = None

        self.center_x = env_int("SCREEN_WIDTH", "1920") // 2
        self.center_y = env_int("SCREEN_HEIGHT", "1080") // 2

        self.delta_x = 0
        self.delta_y = 0

        listener = Listener(on_move=self._on_move)

        thread = threading.Thread(target=listener.start)
        thread.daemon = True
        thread.start()

        self._initialized = True

    def _on_move(self, x: int, y: int) -> None:
        if not self.hook or self.mouse is None:
            return

        dx = x - self.center_x
        dy = y - self.center_y

        if dx != 0 or dy != 0:
            self.delta_x += dx
            self.delta_y += dy

            self.mouse.position = (self.center_x, self.center_y)

    def peek_delta(self) -> tuple[int, int]:
        return (self.delta_x, self.delta_y)

    def consume_delta(self) -> tuple[int, int]:
        dx = self.delta_x
        dy = self.delta_y
        self.delta_x = 0
        self.delta_y = 0
        return dx, dy

    def toggle(self) -> None:
        self.hook = not self.hook

        if self.hook:
            if self.mouse is None:
                self.mouse = Controller()
            self.mouse.position = (self.center_x, self.center_y)
            self.delta_x = 0
            self.delta_y = 0
        else:
            self.mouse = None
            self.delta_x = 0
            self.delta_y = 0
