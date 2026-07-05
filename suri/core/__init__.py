"""Suri core: the frontend-agnostic, provider-agnostic engine."""

from suri.core.agent import Agent
from suri.core.events import StreamEvent, TextChunk, TurnComplete
from suri.core.providers import PROVIDERS, ProviderSpec, get_provider, is_configured, list_models, set_api_key

__all__ = [
    "PROVIDERS",
    "Agent",
    "ProviderSpec",
    "StreamEvent",
    "TextChunk",
    "TurnComplete",
    "get_provider",
    "is_configured",
    "list_models",
    "set_api_key",
]
