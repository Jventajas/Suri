"""SuriApp: starts on the onboarding screen, moves to chat once resolved."""

import time

from textual.app import App
from textual.binding import Binding
from textual.widgets import Static

from suri.cli.screens.chat import ChatScreen
from suri.cli.screens.onboarding import OnboardingScreen
from suri.core import load_selection

QUIT_CONFIRM_WINDOW = 1.5  # seconds within which a second Ctrl+C must land to actually quit


class SuriApp(App[None]):
    """Top-level Textual app; owns screen transitions."""

    BINDINGS = [
        Binding("ctrl+c", "request_quit", "Quit (^C twice)"),
        Binding("ctrl+q", "request_quit", show=False),
    ]
    ENABLE_COMMAND_PALETTE = False

    def __init__(self) -> None:
        super().__init__()
        self._quit_armed_at: float | None = None

    def on_mount(self) -> None:
        selection = load_selection()
        if selection is not None:
            provider_id, model_id = selection
            self.push_screen(ChatScreen(provider_id, model_id))  # pyright: ignore[reportUnknownMemberType]
        else:
            self.push_screen(OnboardingScreen(), self._start_chat)  # pyright: ignore[reportUnknownMemberType]

    def _start_chat(self, selection: tuple[str, str] | None) -> None:
        if selection is None:
            # Textual's dismiss() allows a resultless call regardless of the screen's declared
            # result type; OnboardingScreen never does this, so reaching here is a framework-level
            # invariant violation, not a legitimate "skipped" state.
            raise RuntimeError("Suri couldn't start the chat after onboarding — please restart the app.")
        provider_id, model_id = selection
        self.push_screen(ChatScreen(provider_id, model_id))  # pyright: ignore[reportUnknownMemberType]

    def action_request_quit(self) -> None:
        """First Ctrl+C arms a confirmation window; a second press within it exits.

        Replaces Textual's default `help_quit` (a toast notification) with an inline
        hint on the active screen — same two-press convention as Claude Code/Codex.
        """
        now = time.monotonic()
        if self._quit_armed_at is not None and now - self._quit_armed_at <= QUIT_CONFIRM_WINDOW:
            self.exit()
            return
        self._quit_armed_at = now
        hint = Static("Press Ctrl+C again to exit", id="quit-hint")
        hint.styles.dock = "bottom"
        self.screen.mount(hint)
        self.set_timer(QUIT_CONFIRM_WINDOW, lambda: self._disarm_quit(hint))

    def _disarm_quit(self, hint: Static) -> None:
        self._quit_armed_at = None
        if hint.is_mounted:
            hint.remove()


def main() -> None:
    SuriApp().run()
