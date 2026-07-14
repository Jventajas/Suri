"""Agent core: LangGraph graph + provider-agnostic model."""

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any

from deepagents import create_deep_agent  # pyright: ignore[reportUnknownVariableType]
from langchain_core.messages import AIMessageChunk, BaseMessage

from suri.core.events import RetryAttempt, StreamError, StreamEvent, TextChunk, TurnComplete
from suri.core.models import build_model, is_retryable_error

SYSTEM_PROMPT = "You are Suri, an assistant for mathematical research."

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds; doubles each attempt


class Agent:
    """Single deepagents/LangGraph agent."""

    def __init__(self, provider_id: str, model_id: str) -> None:
        # deepagents' compiled graph is only partially typed; pin to Any at this boundary.
        self._graph: Any = create_deep_agent(
            model=build_model(provider_id, model_id),
            tools=[],
            system_prompt=SYSTEM_PROMPT,
        )

    async def _translate_graph_events(self, history: Sequence[BaseMessage]) -> AsyncIterator[StreamEvent]:
        """Run the graph once, translating LangGraph events into Suri's `StreamEvents."""
        graph_events: AsyncIterator[tuple[BaseMessage, dict[str, Any]]] = self._graph.astream(
            {"messages": list(history)},
            stream_mode="messages",
        )
        async for message, _meta in graph_events:
            # Only assistant text becomes an event; other chunks (tool calls, metadata) are dropped for now.
            if isinstance(message, AIMessageChunk) and message.text:
                yield TextChunk(message.text)

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
