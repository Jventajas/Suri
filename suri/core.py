"""Agent core: LangGraph graph + hardcoded model."""

from collections.abc import Iterator, Sequence
from typing import Any

from deepagents import create_deep_agent  # pyright: ignore[reportUnknownVariableType]
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_ollama import ChatOllama

MODEL_ID = "qwen3:14b"
OLLAMA_BASE_URL = "http://localhost:11434"

SYSTEM_PROMPT = "You are Suri, an assistant for mathematical research."


def build_model() -> BaseChatModel:
    """Hot-swap seam: returns the chat model behind the provider-agnostic interface."""
    return ChatOllama(model=MODEL_ID, base_url=OLLAMA_BASE_URL)


class Agent:
    """Single deepagents/LangGraph agent."""

    def __init__(self) -> None:
        # deepagents' compiled graph is only partially typed; pin to Any at this boundary.
        self._graph: Any = create_deep_agent(
            model=build_model(),
            tools=[],
            system_prompt=SYSTEM_PROMPT,
        )

    def stream(self, history: Sequence[BaseMessage]) -> Iterator[str]:
        """Stream assistant response tokens for the given message history."""
        events: Iterator[tuple[BaseMessage, dict[str, Any]]] = self._graph.stream(
            {"messages": list(history)},
            stream_mode="messages",
        )
        for message, _meta in events:
            if isinstance(message, AIMessageChunk) and message.text:
                yield message.text
