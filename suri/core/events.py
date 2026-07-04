"""Stream events emitted by Agent.stream(); the frontend-agnostic contract."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A piece of assistant response text."""

    text: str


@dataclass(frozen=True, slots=True)
class TurnComplete:
    """Signals the assistant has finished its turn."""


# Frontend-agnostic contract: any frontend (CLI, GUI, API gateway) consumes
# this union, never the underlying LangGraph/model event types directly.
StreamEvent = TextChunk | TurnComplete
