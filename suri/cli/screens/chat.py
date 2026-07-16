"""Chat screen: the REPL loop against a resolved provider/model."""

from dataclasses import dataclass
from typing import assert_never

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from suri.cli.latex import typeset_math
from suri.cli.screens.login import LoginScreen
from suri.cli.screens.model_picker import ModelChoice, ModelScreen
from suri.core import (
    Agent,
    RetryAttempt,
    StreamError,
    TextChunk,
    TodoListUpdated,
    ToolCall,
    ToolResult,
    TurnComplete,
    save_selection,
)


@dataclass(frozen=True, slots=True)
class Command:
    """A slash command available in the chat input's command menu."""

    name: str
    description: str


COMMANDS: tuple[Command, ...] = (
    Command("login", "Add or replace a provider's API key"),
    Command("model", "Switch the active provider/model"),
)

# The model sees full tool results; the human just needs the gist.
TOOL_RESULT_DISPLAY_BUDGET = 200  # characters

# One line per task: done = green tick, active = highlighted, pending = dimmed.
_TODO_LINE_STYLES = {
    "completed": "[green]☑[/] [dim]{}[/]",
    "in_progress": "[bold yellow]☐ {}[/]",
    "pending": "[dim]☐ {}[/]",
}


@dataclass(frozen=True, slots=True)
class Chatting:
    """Default mode: input goes to the agent, or opens the command menu on `/`."""


@dataclass(frozen=True, slots=True)
class PickingCommand:
    """Input narrows the `/` command menu."""


Mode = Chatting | PickingCommand


class ChatScreen(Screen[None]):
    """Textual screen for chatting with the Suri agent."""

    CSS = """
    #model-status {
        padding: 1 1 1 0;
        content-align: right middle;
    }
    """

    BINDINGS = [
        Binding("up", "menu_cursor_up", show=False),
        Binding("down", "menu_cursor_down", show=False),
        Binding("escape", "cancel_picker", show=False),
    ]

    def __init__(self, provider_id: str, model_id: str) -> None:
        super().__init__()
        self._provider_id = provider_id
        self._model_id = model_id
        self._agent = Agent(provider_id, model_id)
        self._history: list[BaseMessage] = []
        self._mode: Mode = Chatting()

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="transcript")
        yield OptionList(id="command-menu")
        yield Input(placeholder="Type a message… ('exit' to leave, '/' for commands)")
        yield Static(id="model-status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#command-menu", OptionList).display = False
        self._update_model_status()
        self.query_one(Input).focus()

    def _update_model_status(self) -> None:
        self.query_one("#model-status", Static).update(f"({self._provider_id}) {self._model_id}")

    def on_input_changed(self, event: Input.Changed) -> None:
        match self._mode:
            case Chatting():
                if event.value.startswith("/"):
                    self._mode = PickingCommand()
                    self._filter_commands(event.value[1:])
            case PickingCommand():
                if not event.value.startswith("/"):
                    self._reset_to_chatting()
                else:
                    self._filter_commands(event.value[1:])
            case _:
                assert_never(self._mode)

    def _filter_commands(self, filter_text: str) -> None:
        menu = self.query_one("#command-menu", OptionList)
        menu.clear_options()
        for command in COMMANDS:
            if filter_text in command.name:
                menu.add_option(Option(f"/{command.name} — {command.description}", id=command.name))
        menu.display = True
        if menu.option_count:
            menu.action_first()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "command-menu" and event.option.id is not None:
            self._reset_to_chatting()
            self._run_command(event.option.id)

    def action_menu_cursor_up(self) -> None:
        menu = self.query_one("#command-menu", OptionList)
        if menu.display:
            menu.action_cursor_up()

    def action_menu_cursor_down(self) -> None:
        menu = self.query_one("#command-menu", OptionList)
        if menu.display:
            menu.action_cursor_down()

    def action_cancel_picker(self) -> None:
        match self._mode:
            case Chatting():
                pass
            case PickingCommand():
                self._reset_to_chatting()
            case _:
                assert_never(self._mode)

    def _reset_to_chatting(self) -> None:
        self._mode = Chatting()
        self.query_one("#command-menu", OptionList).display = False
        input_widget = self.query_one(Input)
        input_widget.value = ""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        match self._mode:
            case Chatting():
                self._submit_message(event.value.strip())
            case PickingCommand():
                menu = self.query_one("#command-menu", OptionList)
                highlighted = menu.highlighted_option
                self._reset_to_chatting()
                if highlighted is not None and highlighted.id is not None:
                    self._run_command(highlighted.id)
            case _:
                assert_never(self._mode)

    def _run_command(self, name: str) -> None:
        if name == "login":
            self.app.push_screen(LoginScreen(), self._refocus_input)  # pyright: ignore[reportUnknownMemberType]
        elif name == "model":
            self.app.push_screen(ModelScreen(), self._on_model_picked)  # pyright: ignore[reportUnknownMemberType]

    def _refocus_input(self, _: None) -> None:
        self.query_one(Input).focus()

    def _on_model_picked(self, choice: ModelChoice | None) -> None:
        if choice is not None:
            self._agent = Agent(choice.provider_id, choice.model_id)
            self._provider_id = choice.provider_id
            self._model_id = choice.model_id
            save_selection(choice.provider_id, choice.model_id)
            self._update_model_status()
        self.query_one(Input).focus()

    def _submit_message(self, value: str) -> None:
        input_widget = self.query_one(Input)
        input_widget.value = ""
        if not value:
            return
        if value == "exit":
            self.app.exit()  # pyright: ignore[reportUnknownMemberType]
            return

        transcript = self.query_one("#transcript", VerticalScroll)
        transcript.mount(Static(f"[bold cyan]you:[/] {typeset_math(value)}"))
        reply_widget = Static("[bold magenta]suri:[/] [dim]…[/]")
        transcript.mount(reply_widget)
        transcript.scroll_end(animate=False)

        self._history.append(HumanMessage(value))
        input_widget.disabled = True
        self._stream_reply(reply_widget)

    @work
    async def _stream_reply(self, reply_widget: Static) -> None:
        reply = ""  # the whole turn's text, for history
        segment = ""  # only the text in the current widget (tool lines split the reply into segments)
        plan_widget: Static | None = None  # the turn's plan block, updated in place
        async for stream_event in self._agent.stream(self._history):
            match stream_event:
                case TextChunk(text=text):
                    reply += text
                    segment += text
                    self._render_reply(reply_widget, segment)
                case RetryAttempt(attempt=attempt, max_attempts=max_attempts, delay=delay):
                    reply_widget.update(f"[dim]suri: retrying ({attempt}/{max_attempts}) in {delay:.0f}s…[/]")
                case StreamError(message=message):
                    reply_widget.update(f"[bold red]suri: {message}[/]")
                case ToolCall(name=name, args=args):
                    compact_args = ", ".join(f"{key}={value!r}" for key, value in args.items())
                    _, reply_widget, segment = self._insert_line(f"[dim]⚙ {name}({compact_args})[/]", reply_widget, segment)
                case ToolResult(name=name, content=content):
                    if len(content) > TOOL_RESULT_DISPLAY_BUDGET:
                        content = content[:TOOL_RESULT_DISPLAY_BUDGET] + "…"
                    _, reply_widget, segment = self._insert_line(f"[dim]→ {name}: {content}[/]", reply_widget, segment)
                case TodoListUpdated(todos=todos):
                    plan = "\n".join(_TODO_LINE_STYLES[item.status].format(item.content) for item in todos)
                    if plan_widget is None:
                        plan_widget, reply_widget, segment = self._insert_line(plan, reply_widget, segment)
                    else:
                        plan_widget.update(plan)
                case TurnComplete():
                    # The reply is final now: redraw it with its formulas typeset.
                    if segment:
                        self._render_reply(reply_widget, typeset_math(segment))
                case _:
                    assert_never(stream_event)
        if reply:
            self._history.append(AIMessage(reply))

        input_widget = self.query_one(Input)
        input_widget.disabled = False
        input_widget.focus()

    def _insert_line(self, markup: str, reply_widget: Static, segment: str) -> tuple[Static, Static, str]:
        """Mount a transcript line, keeping the streaming reply widget last; returns (line, reply, segment)."""
        transcript = self.query_one("#transcript", VerticalScroll)
        line_widget = Static(markup)
        if segment:
            # The current widget already shows text: keep it as-is and stream what follows into a fresh one.
            transcript.mount(line_widget)
            reply_widget = Static("")
            transcript.mount(reply_widget)
        else:
            transcript.mount(line_widget, before=reply_widget)
        transcript.scroll_end(animate=False)
        return line_widget, reply_widget, ""

    def _render_reply(self, widget: Static, text: str) -> None:
        widget.update(f"[bold magenta]suri:[/] {text}")
        self.query_one("#transcript", VerticalScroll).scroll_end(animate=False)
