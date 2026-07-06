"""Chat screen: the REPL loop against a resolved provider/model."""

from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from suri.core import Agent, TextChunk, TurnComplete


@dataclass(frozen=True, slots=True)
class Command:
    """A slash command available in the chat input's command menu."""

    name: str
    description: str


COMMANDS: tuple[Command, ...] = (
    Command("login", "Add or replace a provider's API key"),
    Command("model", "Switch the active provider/model"),
)


class ChatScreen(Screen[None]):
    """Textual screen for chatting with the Suri agent."""

    BINDINGS = [
        Binding("up", "menu_cursor_up", show=False),
        Binding("down", "menu_cursor_down", show=False),
    ]

    def __init__(self, provider_id: str, model_id: str) -> None:
        super().__init__()
        self._agent = Agent(provider_id, model_id)
        self._history: list[BaseMessage] = []

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="transcript")
        yield OptionList(id="command-menu")
        yield Input(placeholder="Type a message… ('exit' to leave, '/' for commands)")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#command-menu", OptionList).display = False
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        menu = self.query_one("#command-menu", OptionList)
        if not event.value.startswith("/"):
            menu.display = False
            return
        filter_text = event.value[1:]
        menu.clear_options()
        for command in COMMANDS:
            if filter_text in command.name:
                menu.add_option(Option(f"/{command.name} — {command.description}", id=command.name))
        menu.display = True
        if menu.option_count:
            menu.action_first()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "command-menu" and event.option.id is not None:
            self._run_command(event.option.id)

    def action_menu_cursor_up(self) -> None:
        menu = self.query_one("#command-menu", OptionList)
        if menu.display:
            menu.action_cursor_up()

    def action_menu_cursor_down(self) -> None:
        menu = self.query_one("#command-menu", OptionList)
        if menu.display:
            menu.action_cursor_down()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        menu = self.query_one("#command-menu", OptionList)

        if value.startswith("/"):
            event.input.value = ""
            highlighted = menu.highlighted_option
            if menu.display and highlighted is not None and highlighted.id is not None:
                self._run_command(highlighted.id)
            return

        event.input.value = ""
        if not value:
            return
        if value == "exit":
            self.app.exit()  # pyright: ignore[reportUnknownMemberType]
            return

        transcript = self.query_one("#transcript", VerticalScroll)
        transcript.mount(Static(f"[bold cyan]you:[/] {value}"))
        reply_widget = Static("[bold magenta]suri:[/] [dim]…[/]")
        transcript.mount(reply_widget)
        transcript.scroll_end(animate=False)

        self._history.append(HumanMessage(value))
        event.input.disabled = True
        self._stream_reply(reply_widget)

    def _run_command(self, name: str) -> None:
        self.query_one("#command-menu", OptionList).display = False

    @work
    async def _stream_reply(self, reply_widget: Static) -> None:
        reply = ""
        async for stream_event in self._agent.stream(self._history):
            match stream_event:
                case TextChunk(text=text):
                    reply += text
                    self._render_reply(reply_widget, reply)
                case TurnComplete():
                    pass
        self._history.append(AIMessage(reply))

        input_widget = self.query_one(Input)
        input_widget.disabled = False
        input_widget.focus()

    def _render_reply(self, widget: Static, text: str) -> None:
        widget.update(f"[bold magenta]suri:[/] {text}")
        self.query_one("#transcript", VerticalScroll).scroll_end(animate=False)
