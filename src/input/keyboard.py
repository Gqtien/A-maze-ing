import threading
from pynput.keyboard import Key, KeyCode, Listener


class KeyboardHandler:
    """
    Manages keyboard input in a separate thread.
    Singleton: only one instance exists.
    """

    _instance: "KeyboardHandler | None" = None

    def __new__(cls) -> "KeyboardHandler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Start the keyboard listener in a separate thread on first call."""
        if getattr(self, "_initialized", False):
            return

        self.keys_pressed: set[str | Key] = set()

        listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )

        listener_thread = threading.Thread(target=listener.start)
        listener_thread.daemon = True
        listener_thread.start()

        self._initialized = True

    def _on_press(self, key: Key | KeyCode | None) -> None:
        """Key press callback."""
        if isinstance(key, KeyCode) and key.char is not None:
            self.keys_pressed.add(key.char)
        elif isinstance(key, Key):
            self.keys_pressed.add(key)

    def _on_release(self, key: Key | KeyCode | None) -> None:
        """Key release callback."""
        if isinstance(key, KeyCode) and key.char is not None:
            self.keys_pressed.discard(key.char)
        elif isinstance(key, Key):
            self.keys_pressed.discard(key)
