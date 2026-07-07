"""Login screen: add or replace a provider's API key, without touching the active model."""

from dataclasses import dataclass
from typing import assert_never

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from suri.core import PROVIDERS, is_configured, set_api_key

API_KEY_PROVIDERS = tuple(provider for provider in PROVIDERS if provider.requires_api_key)


@dataclass(frozen=True, slots=True)
class SelectingProvider:
    """Initial step: no provider chosen yet."""


@dataclass(frozen=True, slots=True)
class EnteringApiKey:
    """Provider chosen; typing its API key."""

    provider_id: str


Step = SelectingProvider | EnteringApiKey


class LoginScreen(ModalScreen[None]):
    """Stores an API key for a provider on top of the current chat — the active
    provider/model selection is untouched; this only adds/replaces a credential.

    A compact overlay anchored above the chat input, like `ModelScreen` — the pattern
    every command that needs its own UI should follow.
    """

    BINDINGS = [("escape", "go_back", "Back")]

    CSS = """
    LoginScreen {
        align: center bottom;
    }
    #login-box {
        width: 100%;
        height: auto;
        max-height: 60%;
        /* 7 = ChatScreen's Input (3 rows) + #model-status (3 rows) + Footer (1 row) below it */
        margin-bottom: 7;
        padding: 1 2;
        background: $panel;
        border: tall $border;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._step: Step = SelectingProvider()

    def compose(self) -> ComposeResult:
        with Vertical(id="login-box"):
            yield Static("Log in to a provider — this won't change your active model (Esc to cancel):")
            options = [
                Option(f"{'✓ ' if is_configured(provider) else '  '}{provider.name}", id=provider.id)
                for provider in API_KEY_PROVIDERS
            ]
            yield OptionList(*options, id="login-provider-list")
            yield Input(placeholder="API key…", password=True, id="login-api-key-input")

    def on_mount(self) -> None:
        self._enter_step(self._step)

    def _enter_step(self, step: Step) -> None:
        """Set the current step and show only the widget for it — one step visible at a time."""
        self._step = step
        provider_list = self.query_one("#login-provider-list", OptionList)
        api_key_input = self.query_one("#login-api-key-input", Input)
        match step:
            case SelectingProvider():
                provider_list.display = True
                api_key_input.display = False
                provider_list.focus()
            case EnteringApiKey():
                provider_list.display = False
                api_key_input.display = True
                api_key_input.value = ""
                api_key_input.focus()
            case _:
                assert_never(step)

    def action_go_back(self) -> None:
        match self._step:
            case SelectingProvider():
                self.dismiss()
            case EnteringApiKey():
                self._enter_step(SelectingProvider())
            case _:
                assert_never(self._step)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        provider_id = event.option.id
        if provider_id is None:
            raise RuntimeError("Suri hit an unexpected error selecting a provider — please restart the app.")
        self._enter_step(EnteringApiKey(provider_id))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        api_key = event.value.strip()
        if not api_key:
            return
        match self._step:
            case EnteringApiKey(provider_id=provider_id):
                set_api_key(provider_id, api_key)
                self.dismiss()
            case SelectingProvider():
                raise RuntimeError(
                    f"Suri received an API key while in step {self._step!r} — please restart the app."
                )
            case _:
                assert_never(self._step)
