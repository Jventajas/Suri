"""CLI entry point: REPL loop."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Input, Static

from suri.core import Agent, TextChunk, TurnComplete


class SuriApp(App[None]):
    """Textual REPL for chatting with the Suri agent."""

    BINDINGS = [("ctrl+d", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self._agent = Agent()
        self._history: list[BaseMessage] = []

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="transcript")
        yield Input(placeholder="Type a message… (exit/quit to leave)")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        message = event.value.strip()
        event.input.value = "" # Clear prompt window.
        if not message:
            return
        if message in ("exit", "quit"):
            self.exit()
            return

        transcript = self.query_one("#transcript", VerticalScroll)
        transcript.mount(Static(f"[bold cyan]you:[/] {message}"))
        reply_widget = Static("[bold magenta]suri:[/] [dim]…[/]")
        transcript.mount(reply_widget)
        transcript.scroll_end(animate=False)

        self._history.append(HumanMessage(message))
        event.input.disabled = True
        self._stream_reply(reply_widget)

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


def main() -> None:
    SuriApp().run()
