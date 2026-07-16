"""Agent core: LangGraph graph + provider-agnostic model."""

import asyncio
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from deepagents import create_deep_agent  # pyright: ignore[reportUnknownVariableType]
from langchain_core.messages import AIMessageChunk, BaseMessage, ToolMessage

from suri.core.events import (
    RetryAttempt,
    StreamError,
    StreamEvent,
    TextChunk,
    TodoItem,
    TodoListUpdated,
    ToolCall,
    ToolResult,
    TurnComplete,
)
from suri.core.models import build_model, is_retryable_error
from suri.core.tools import AGENT_TOOLS

SYSTEM_PROMPT = (
    "You are Suri, an assistant for mathematical research. "
    "Verify every nontrivial mathematical claim with your tools before asserting it — "
    "an unverified step can silently invalidate a researcher's result. "
    "If a tool call fails, read the error, fix the input, and retry."
)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds; doubles each attempt


def _events_from_model_chunk(chunk: AIMessageChunk) -> Iterator[StreamEvent]:
    """Translate one chunk of the model's reply into events: tool requests, plan updates, and text."""
    for call in chunk.tool_calls:
        if call["name"] == "write_todos":
            # write_todos is how the model rewrites its own plan: the new list comes in the args.
            items = call["args"]["todos"]
            todos = tuple(TodoItem(item["content"], item["status"]) for item in items)
            # yield an event declaring the progress we've made on the plan.
            yield TodoListUpdated(todos)
        else:
            yield ToolCall(call["name"], call["args"])
    if chunk.text:
        yield TextChunk(chunk.text)


def _events_from_tool_result(message: ToolMessage) -> Iterator[StreamEvent]:
    """Translate a finished tool's result into an event."""
    if message.name == "write_todos":
        # Its result only echoes the plan, already shown when the model wrote it.
        return
    yield ToolResult(message.name or "", message.text)


class Agent:
    """Single deepagents/LangGraph agent."""

    def __init__(self, provider_id: str, model_id: str) -> None:
        # deepagents' compiled graph is only partially typed; pin to Any at this boundary.
        self._graph: Any = create_deep_agent(
            model=build_model(provider_id, model_id),
            tools=list(AGENT_TOOLS),
            system_prompt=SYSTEM_PROMPT,
        )

    async def _translate_graph_events(self, history: Sequence[BaseMessage]) -> AsyncIterator[StreamEvent]:
        """Run the graph once, translating each LangGraph message into a Suri `StreamEvent`."""
        graph_events: AsyncIterator[tuple[BaseMessage, dict[str, object]]] = self._graph.astream(
            {"messages": list(history)},
            stream_mode="messages",
        )
        async for message, _meta in graph_events:
            # A message is either from the model (a piece of its reply) or from a tool (its result).
            if isinstance(message, AIMessageChunk):
                for event in _events_from_model_chunk(message):
                    yield event
            elif isinstance(message, ToolMessage):
                for event in _events_from_tool_result(message):
                    yield event

    async def stream(self, history: Sequence[BaseMessage]) -> AsyncIterator[StreamEvent]:
        """Stream assistant response events; failures surface as events, never raw exceptions."""
        for attempt in range(1, MAX_RETRIES + 1):
            output_already_streamed = False
            try:
                async for event in self._translate_graph_events(history):
                    output_already_streamed = True
                    yield event
                break
            except Exception as error:
                # No retry once partial output streamed — restarting would duplicate it.
                if output_already_streamed or not is_retryable_error(error) or attempt >= MAX_RETRIES:
                    yield StreamError(str(error))
                    break
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                yield RetryAttempt(attempt=attempt, max_attempts=MAX_RETRIES, delay=delay, error_message=str(error))
                await asyncio.sleep(delay)
        yield TurnComplete()
