import threading
from pynput import keyboard

keys_pressed: set[str | keyboard.Key] = set()


def on_press(key: keyboard.Key) -> None:
    """Key press callback."""
    try:
        keys_pressed.add(key.char)
    except AttributeError:
        keys_pressed.add(key)


def on_release(key: keyboard.Key) -> None:
    """Key release callback."""
    try:
        keys_pressed.remove(key.char)
    except AttributeError:
        keys_pressed.remove(key)
    except KeyError:
        pass


class KeyboardHandler:
    """Manages keyboard input in a separate thread."""

    def __init__(self) -> None:
        """Start the keyboard listener in a separate thread."""
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener_thread = threading.Thread(target=listener.start)
        listener_thread.daemon = True
        listener_thread.start()
