"""Onboarding screen: mandatory provider + API key + model selection before chat."""

from dataclasses import dataclass
from typing import assert_never

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from suri.core import PROVIDERS, get_provider, list_models, save_selection, set_api_key


@dataclass(frozen=True, slots=True)
class SelectingProvider:
    """Initial step: no provider chosen yet."""


@dataclass(frozen=True, slots=True)
class SelectingApiKey:
    """Provider chosen, requires an API key that isn't stored yet."""

    provider_id: str


@dataclass(frozen=True, slots=True)
class SelectingModel:
    """Provider resolved; picking a model. `api_key` is only set if just typed this session
    (not yet written to keyring) — `None` if the provider needs none, or one was already stored."""

    provider_id: str
    api_key: str | None


Step = SelectingProvider | SelectingApiKey | SelectingModel


class OnboardingScreen(Screen[tuple[str, str]]):
    """Walks the user through provider -> API key -> model, in that order.

    Cannot be skipped or left empty — the only way out is dismissing with a resolved
    (provider_id, model_id) pair. Nothing is persisted (API key, selection) until that
    dismissal, and `Escape` steps back to provider selection at any point, so a
    restart/back navigation never leaves a half-configured provider behind.
    """

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._step: Step = SelectingProvider()

    def compose(self) -> ComposeResult:
        with Vertical(id="onboarding"):
            yield Static("Welcome to Suri — choose a provider to get started:")
            options = [Option(provider.name, id=provider.id) for provider in PROVIDERS]
            yield OptionList(*options, id="provider-list")
            yield Input(placeholder="API key…", password=True, id="api-key-input")
            yield OptionList(id="model-list")
        yield Footer()

    def on_mount(self) -> None:
        self._enter_step(self._step)

    def _enter_step(self, step: Step) -> None:
        """Set the current step and show only the widget for it — one step visible at a time."""
        self._step = step
        provider_list = self.query_one("#provider-list", OptionList)
        api_key_input = self.query_one("#api-key-input", Input)
        model_list = self.query_one("#model-list", OptionList)
        match step:
            case SelectingProvider():
                provider_list.display = True
                api_key_input.display = False
                model_list.display = False
                provider_list.focus()
            case SelectingApiKey():
                provider_list.display = False
                api_key_input.display = True
                api_key_input.value = ""
                model_list.display = False
                api_key_input.focus()
            case SelectingModel():
                provider_list.display = False
                api_key_input.display = False
                model_list.display = True
                model_list.clear_options()
                model_list.focus()
            case _:
                assert_never(step)

    def action_go_back(self) -> None:
        match self._step:
            case SelectingProvider():
                pass
            case SelectingApiKey() | SelectingModel():
                self._enter_step(SelectingProvider())
            case _:
                assert_never(self._step)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "provider-list":
            self._select_provider(event.option.id)
        elif event.option_list.id == "model-list":
            self._select_model(event.option.id)

    def _select_provider(self, provider_id: str | None) -> None:
        if provider_id is None:
            raise RuntimeError("Suri hit an unexpected error selecting a provider — please restart the app.")
        provider = get_provider(provider_id)

        if provider.requires_api_key:
            self._enter_step(SelectingApiKey(provider_id))
        else:
            self._enter_step(SelectingModel(provider_id, api_key=None))
            self._load_models(provider_id)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        api_key = event.value.strip()
        if not api_key:
            return
        match self._step:
            case SelectingApiKey(provider_id=provider_id):
                self._enter_step(SelectingModel(provider_id, api_key=api_key))
                self._load_models(provider_id)
            case SelectingProvider() | SelectingModel():
                raise RuntimeError(
                    f"Suri received an API key while in step {self._step!r} — please restart the app."
                )
            case _:
                assert_never(self._step)

    @work(thread=True)
    def _load_models(self, provider_id: str) -> None:
        models = list_models(provider_id)
        self.app.call_from_thread(self._show_models, provider_id, models)  # pyright: ignore[reportUnknownMemberType]

    def _show_models(self, provider_id: str, models: list[str]) -> None:
        if not isinstance(self._step, SelectingModel) or self._step.provider_id != provider_id:
            return  # user navigated away before this load finished
        model_list = self.query_one("#model-list", OptionList)
        for model_id in models:
            model_list.add_option(Option(model_id, id=model_id))
        model_list.focus()

    def _select_model(self, model_id: str | None) -> None:
        if model_id is None:
            raise RuntimeError("Suri hit an unexpected error selecting a model — please restart the app.")
        match self._step:
            case SelectingModel(provider_id=provider_id, api_key=api_key):
                if api_key is not None:
                    set_api_key(provider_id, api_key)
                save_selection(provider_id, model_id)
                self.dismiss((provider_id, model_id))
            case SelectingProvider() | SelectingApiKey():
                raise RuntimeError(
                    f"Suri received a model selection while in step {self._step!r} — please restart the app."
                )
            case _:
                assert_never(self._step)
