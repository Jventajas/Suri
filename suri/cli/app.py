"""SuriApp: starts on the onboarding screen, moves to chat once resolved."""

from textual.app import App

from suri.cli.screens.chat import ChatScreen
from suri.cli.screens.onboarding import OnboardingScreen
from suri.core import load_selection


class SuriApp(App[None]):
    """Top-level Textual app; owns screen transitions."""

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


def main() -> None:
    SuriApp().run()
