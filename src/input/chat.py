import string
import time
from collections.abc import Callable
from typing import Set
from pynput import keyboard
from input import KeyboardHandler

CommandResult = tuple[str | None, bool] | None


def _is_printable_key(key) -> bool:
    return (
        isinstance(key, str)
        and len(key) == 1
        and key in string.printable
        and key != ":"
    )


class ChatHandler:
    """Handles chat overlay and /commands."""

    def __init__(self) -> None:
        self.keyboard_handler: KeyboardHandler = KeyboardHandler()
        self.is_open: bool = False
        self.messages: list[tuple[str, bytes]] = []
        self.input_buffer: str = "/"
        self._commands: dict[str, Callable[[list[str]], CommandResult]] = {}
        self._command_displays: dict[str, str] = {}
        self._slash_was_pressed: bool = False
        self._escape_was_pressed: bool = False
        self._prev_keys_pressed: Set[str | keyboard.Key] = set()
        self.default_color: bytes = b"\xFF\xFF\xFF\xFF"
        self.error_color: bytes = b"\x00\x00\xFF\xFF"
        self._command_history: list[str] = []
        self._history_index: int = 0
        self._buffer_before_history: str = "/"
        self._cursor_visible: bool = True
        self._cursor_last_toggle_ns: int = 0
        self._register_builtins()

    def _register_builtins(self) -> None:
        def help_cmd(_args: list[str]) -> None:
            names = ", ".join(
                f"/{self._command_displays.get(n, n)}"
                for n in list(self._commands.keys())[1:]
            )
            self.messages.append((f"Commands: {names}", self.default_color))

        self._commands["help"] = help_cmd

    def register_command(
        self,
        name: str,
        callback: Callable[[list[str]], CommandResult],
        display: str | None = None,
    ) -> None:
        """Register a command."""
        self._commands[name] = callback
        if display is not None:
            self._command_displays[name] = display

    def get_display_text(self) -> str:
        """Return the current input buffer with blinking cursor at end."""
        cursor = "_" if self._cursor_visible else " "
        return self.input_buffer + cursor

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
        keys_pressed = self.keyboard_handler.keys_pressed
        slash_pressed = ":" in keys_pressed
        escape_pressed = keyboard.Key.esc in keys_pressed

        self._update_toggle_and_escape(slash_pressed, escape_pressed)

        if self.is_open:
            self._update_cursor_blink()
            self._process_new_keys(keys_pressed)

        self._prev_keys_pressed = keys_pressed.copy()

    def _update_toggle_and_escape(
        self, slash_pressed: bool, escape_pressed: bool
    ) -> None:
        if slash_pressed and not self._slash_was_pressed:
            self.is_open = not self.is_open
            if not self.is_open:
                self._prev_keys_pressed = set()
            self.input_buffer = "/"
            self._history_index = len(self._command_history)
        self._slash_was_pressed = slash_pressed

        if self.is_open and escape_pressed and not self._escape_was_pressed:
            self.is_open = False
            self._prev_keys_pressed = set()
        self._escape_was_pressed = escape_pressed

    def _update_cursor_blink(self) -> None:
        now_ns = time.perf_counter_ns()
        if now_ns - self._cursor_last_toggle_ns >= int(0.5 * 1e9):
            self._cursor_visible = not self._cursor_visible
            self._cursor_last_toggle_ns = now_ns

    def _process_new_keys(
        self, keys_pressed: Set[str | keyboard.Key]
    ) -> None:
        new_presses = keys_pressed - self._prev_keys_pressed
        for key in new_presses:
            self._handle_key(key)

    def _handle_key(self, key: str | keyboard.Key) -> None:
        if key == keyboard.Key.up:
            self._handle_history_up()
        elif key == keyboard.Key.down:
            self._handle_history_down()
        elif key == keyboard.Key.backspace:
            self._handle_backspace()
        elif key == keyboard.Key.enter:
            self._handle_enter()
        elif key == keyboard.Key.space:
            self.input_buffer += " "
        elif _is_printable_key(key):
            self.input_buffer += key

    def _handle_history_up(self) -> None:
        if not self._command_history:
            return
        if self._history_index == len(self._command_history):
            self._buffer_before_history = self.input_buffer
        self._history_index = max(0, self._history_index - 1)
        self.input_buffer = self._command_history[self._history_index]

    def _handle_history_down(self) -> None:
        if self._history_index >= len(self._command_history):
            return
        self._history_index += 1
        if self._history_index == len(self._command_history):
            self.input_buffer = self._buffer_before_history
        else:
            self.input_buffer = self._command_history[self._history_index]

    def _handle_backspace(self) -> None:
        if len(self.input_buffer) > 1:
            self.input_buffer = self.input_buffer[:-1]

    def _handle_enter(self) -> None:
        raw = self.input_buffer.strip()
        self.input_buffer = "/"
        self._history_index = len(self._command_history)
        if not raw or not raw.startswith("/"):
            return
        self._execute_command(raw)

    def _execute_command(self, raw: str) -> None:
        parts = raw[1:].strip().split()
        if not parts:
            return
        name = parts[0].lower()
        args = parts[1:]

        if name not in self._commands:
            self.messages.append(
                ("Unknown command. Type /help", self.error_color)
            )
            return

        if (
            not self._command_history
            or self._command_history[-1] != raw
        ):
            self._command_history.append(raw)

        result = self._commands[name](args)
        if result is None:
            return
        msg, close_chat = result
        if msg is not None:
            self.messages.append((msg, self.default_color))
        if close_chat:
            self.is_open = False
