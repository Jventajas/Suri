"""Suri core: the frontend-agnostic, provider-agnostic engine."""

from suri.core.agent import Agent
from suri.core.events import RetryAttempt, StreamError, StreamEvent, TextChunk, TurnComplete
from suri.core.providers import PROVIDERS, ProviderSpec, get_provider, is_configured, list_models, set_api_key
from suri.core.selection import load_selection, save_selection

__all__ = [
    "PROVIDERS",
    "Agent",
    "ProviderSpec",
    "RetryAttempt",
    "StreamError",
    "StreamEvent",
    "TextChunk",
    "TurnComplete",
    "get_provider",
    "is_configured",
    "list_models",
    "load_selection",
    "save_selection",
    "set_api_key",
]
