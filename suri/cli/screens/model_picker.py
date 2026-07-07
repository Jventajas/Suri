"""Model picker screen: filter and pick a provider/model from every configured provider."""

from dataclasses import dataclass

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from suri.core import PROVIDERS, is_configured, list_models


@dataclass(frozen=True, slots=True)
class ModelChoice:
    """A provider/model pair offered by the picker."""

    provider_id: str
    model_id: str


class ModelScreen(ModalScreen[ModelChoice | None]):
    """Compact overlay anchored above the chat input — same pattern as `LoginScreen`.

    Typing filters the catalog by substring; `Enter`/click picks the highlighted entry;
    `Escape` cancels (dismisses with `None`) without touching the active model.
    """

    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "cursor_up", show=False),
        Binding("down", "cursor_down", show=False),
    ]

    CSS = """
    ModelScreen {
        align: center bottom;
    }
    #model-box {
        width: 100%;
        height: auto;
        max-height: 60%;
        /* 7 = ChatScreen's Input (3 rows) + #model-status (3 rows) + Footer (1 row) below it */
        margin-bottom: 7;
        background: $panel;
        border: tall $border;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._choices: tuple[ModelChoice, ...] = ()

    def compose(self) -> ComposeResult:
        with Vertical(id="model-box"):
            yield OptionList(id="model-list")
            yield Input(placeholder="Filter models…")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self._load_choices()

    @work(thread=True)
    def _load_choices(self) -> None:
        choices = tuple(
            ModelChoice(provider.id, model_id)
            for provider in PROVIDERS
            if provider.id == "ollama" or is_configured(provider)
            for model_id in list_models(provider.id)
        )
        self.app.call_from_thread(self._show_choices, choices)  # pyright: ignore[reportUnknownMemberType]

    def _show_choices(self, choices: tuple[ModelChoice, ...]) -> None:
        self._choices = choices
        self._filter("")

    def _filter(self, filter_text: str) -> None:
        menu = self.query_one("#model-list", OptionList)
        menu.clear_options()
        for index, choice in enumerate(self._choices):
            label = f"{choice.provider_id}: {choice.model_id}"
            if filter_text.lower() in label.lower():
                menu.add_option(Option(label, id=str(index)))
        if menu.option_count:
            menu.action_first()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._filter(event.value)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id is not None:
            self.dismiss(self._choices[int(event.option.id)])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        highlighted = self.query_one("#model-list", OptionList).highlighted_option
        if highlighted is not None and highlighted.id is not None:
            self.dismiss(self._choices[int(highlighted.id)])

    def action_cursor_up(self) -> None:
        self.query_one("#model-list", OptionList).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one("#model-list", OptionList).action_cursor_down()

    def action_cancel(self) -> None:
        self.dismiss(None)
