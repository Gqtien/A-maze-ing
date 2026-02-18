import threading
from pynput import keyboard


class KeyboardHandler:
    """Manages keyboard input in a separate thread. Singleton."""

    _instance: "KeyboardHandler | None" = None

    def __new__(cls) -> "KeyboardHandler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Start the keyboard listener in a separate thread."""
        if hasattr(self, "_listener_started"):
            return
        self._listener_started = True
        self.keys_pressed: set[str | keyboard.Key] = set()
        listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        listener_thread = threading.Thread(target=listener.start)
        listener_thread.daemon = True
        listener_thread.start()

    def _on_press(self, key: keyboard.Key) -> None:
        """Key press callback."""
        try:
            self.keys_pressed.add(key.char)
        except AttributeError:
            self.keys_pressed.add(key)

    def _on_release(self, key: keyboard.Key) -> None:
        """Key release callback."""
        try:
            self.keys_pressed.discard(key.char)
        except AttributeError:
            self.keys_pressed.discard(key)
