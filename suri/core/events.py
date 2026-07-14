"""Stream events emitted by Agent.stream(); the frontend-agnostic contract."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A piece of assistant response text."""

    text: str


@dataclass(frozen=True, slots=True)
class TurnComplete:
    """Signals the assistant has finished its turn."""


@dataclass(frozen=True, slots=True)
class RetryAttempt:
    """A retryable provider/model error occurred; a retry is about to happen."""

    attempt: int
    max_attempts: int
    delay: float
    error_message: str


@dataclass(frozen=True, slots=True)
class StreamError:
    """The turn failed: a non-retryable error, or retries were exhausted."""

    message: str


# Frontend-agnostic contract: any frontend (CLI, GUI, API gateway) consumes
# this union, never the underlying LangGraph/model event types directly.
StreamEvent = TextChunk | TurnComplete | RetryAttempt | StreamError
