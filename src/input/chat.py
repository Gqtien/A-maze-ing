import string
from collections.abc import Callable
from typing import Set
from pynput import keyboard
from input import KeyboardHandler


class ChatHandler:
    """Handles chat overlay and /commands."""

    def __init__(self) -> None:
        self.keyboard_handler: KeyboardHandler = KeyboardHandler()
        self.is_open: bool = False
        self.messages: list[tuple[str, bytes]] = []
        self.input_buffer: str = "/"
        self._commands: dict[str, Callable[[], None]] = {}
        self._slash_was_pressed: bool = False
        self._escape_was_pressed: bool = False
        self._prev_keys_pressed: Set[str | keyboard.Key] = set()
        self.default_color: bytes = b"\xFF\xFF\xFF\xFF"
        self.error_color: bytes = b"\x00\x00\xFF\xFF"
        self._register_builtins()

    def _register_builtins(self) -> None:
        def help_cmd() -> None:
            names = ", ".join(f"/{n}" for n in sorted(self._commands.keys()))
            self.messages.append((f"Commands: {names}", self.default_color))

        self._commands["help"] = help_cmd

    def register_command(
        self,
        name: str,
        callback: Callable[[], None],
    ) -> None:
        """Register a command."""
        self._commands[name] = callback

    def get_display_text(self) -> str:
        """Return the current input buffer."""
        return self.input_buffer

    def get_overlay_lines(
        self,
        max_message_lines: int,
    ) -> list[tuple[str, bytes]]:
        """Return (text, color) for each line in the grey zone."""
        if max_message_lines <= 0:
            return [(self.get_display_text(), self.default_color)]
        last = self.messages[-max_message_lines:] if self.messages else []
        return last + [(self.get_display_text(), self.default_color)]

    def update(self) -> None:
        """Update the chat handler."""
        keys_pressed = self.keyboard_handler.keys_pressed
        slash_pressed = ":" in keys_pressed
        escape_pressed = keyboard.Key.esc in keys_pressed

        if slash_pressed and not self._slash_was_pressed:
            self.is_open = not self.is_open
            if not self.is_open:
                self._prev_keys_pressed = set()
            self.input_buffer = "/"
        self._slash_was_pressed = slash_pressed

        if self.is_open and escape_pressed and not self._escape_was_pressed:
            self.is_open = False
            self._prev_keys_pressed = set()
        self._escape_was_pressed = escape_pressed

        if self.is_open:
            new_presses = keys_pressed - self._prev_keys_pressed
            for key in new_presses:
                if key == keyboard.Key.backspace:
                    if len(self.input_buffer) > 1:
                        self.input_buffer = self.input_buffer[:-1]
                elif key == keyboard.Key.enter:
                    raw = self.input_buffer.strip()
                    self.input_buffer = "/"
                    if not raw or not raw.startswith("/"):
                        continue
                    name = raw[1:].strip().lower()
                    if not name:
                        continue
                    if name in self._commands:
                        self._commands[name]()
                    else:
                        self.messages.append(
                            ("Unknown command. Type /help", self.error_color)
                        )
                elif (
                    isinstance(key, str)
                    and len(key) == 1
                    and key in string.printable
                    and key != ":"
                ):
                    self.input_buffer += key
            self._prev_keys_pressed = keys_pressed.copy()
        else:
            self._prev_keys_pressed = keys_pressed.copy()
