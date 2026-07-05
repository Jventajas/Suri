"""Agent core: LangGraph graph + provider-agnostic model."""

from collections.abc import AsyncIterator, Sequence
from typing import Any

from deepagents import create_deep_agent  # pyright: ignore[reportUnknownVariableType]
from langchain_core.messages import AIMessageChunk, BaseMessage

from suri.core.events import StreamEvent, TextChunk, TurnComplete
from suri.core.models import build_model

SYSTEM_PROMPT = "You are Suri, an assistant for mathematical research."


class Agent:
    """Single deepagents/LangGraph agent."""

    def __init__(self, provider_id: str, model_id: str) -> None:
        # deepagents' compiled graph is only partially typed; pin to Any at this boundary.
        self._graph: Any = create_deep_agent(
            model=build_model(provider_id, model_id),
            tools=[],
            system_prompt=SYSTEM_PROMPT,
        )

    async def stream(self, history: Sequence[BaseMessage]) -> AsyncIterator[StreamEvent]:
        """Stream assistant response events for the given message history."""
        events: AsyncIterator[tuple[BaseMessage, dict[str, Any]]] = self._graph.astream(
            {"messages": list(history)},
            stream_mode="messages",
        )
        async for message, _meta in events:
            if isinstance(message, AIMessageChunk) and message.text:
                yield TextChunk(message.text)
        yield TurnComplete()
