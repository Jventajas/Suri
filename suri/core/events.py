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


@dataclass(frozen=True, slots=True)
class ToolCall:
    """The assistant invoked a tool with the given arguments."""

    name: str
    # Model-generated JSON: values are opaque; narrow before operating on them.
    args: dict[str, object]


@dataclass(frozen=True, slots=True)
class ToolResult:
    """A tool finished and returned this content to the assistant."""

    name: str
    content: str


@dataclass(frozen=True, slots=True)
class TodoItem:
    """One task in the assistant's self-written plan."""

    content: str
    status: str  # "pending" | "in_progress" | "completed"


@dataclass(frozen=True, slots=True)
class TodoListUpdated:
    """The assistant updated its plan; carries the full current list."""

    todos: tuple[TodoItem, ...]


# Frontend-agnostic contract: any frontend (CLI, GUI, API gateway) consumes
# this union, never the underlying LangGraph/model event types directly.
StreamEvent = TextChunk | TurnComplete | RetryAttempt | StreamError | ToolCall | ToolResult | TodoListUpdated
