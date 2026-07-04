"""Model provider layer: the hot-swap seam between core and any LLM provider."""

import os

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

# Hardcoded for now; deferred to a future config-loading iteration (see
# roadmap/01_chat_cli.md "Open") — CLI flag > env var > config file > default.
MODEL_ID = "qwen3:14b"
OLLAMA_BASE_URL = "http://localhost:11434"

PROVIDER_ENV_VAR = "SURI_MODEL_PROVIDER"
DEFAULT_PROVIDER = "ollama"


def build_model(provider: str | None = None) -> BaseChatModel:
    """Return the chat model behind the provider-agnostic interface.

    Provider is selected via `provider` or the `SURI_MODEL_PROVIDER` env var,
    defaulting to local Ollama. Add new providers as new match arms here when
    they're actually needed (e.g. Claude/OpenAI in prod).
    """
    provider = provider or os.environ.get(PROVIDER_ENV_VAR, DEFAULT_PROVIDER)
    match provider:
        case "ollama":
            return ChatOllama(model=MODEL_ID, base_url=OLLAMA_BASE_URL)
        case _:
            raise ValueError(f"Unknown model provider: {provider!r}")
