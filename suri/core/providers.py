"""Provider registry: data-driven list of supported model providers.

Credentials are stored via `keyring` — (macOS Keychain / Windows Credential Manager / Linux Secret Service).
"""

import json
from dataclasses import dataclass
from importlib import resources

import httpx
import keyring

KEYRING_SERVICE = "suri-provider"
MODELS_SNAPSHOT = json.loads(resources.files("suri.core.data").joinpath("models_snapshot.json").read_text())


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Static description of a model provider."""

    id: str
    name: str
    base_url: str
    requires_api_key: bool


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(id="ollama", name="Ollama (local)", base_url="http://localhost:11434", requires_api_key=False),
    ProviderSpec(id="minimax", name="MiniMax", base_url="https://api.minimax.io/v1", requires_api_key=True),
    ProviderSpec(id="zai", name="Z.ai", base_url="https://api.z.ai/api/coding/paas/v4", requires_api_key=True),
)


def get_provider(provider_id: str) -> ProviderSpec:
    """Look up a provider spec by id."""
    for provider in PROVIDERS:
        if provider.id == provider_id:
            return provider
    raise ValueError(f"Unknown provider: {provider_id!r}")


def set_api_key(provider_id: str, api_key: str) -> None:
    """Store a provider's API key in the OS keychain."""
    keyring.set_password(KEYRING_SERVICE, provider_id, api_key)


def get_api_key(provider_id: str) -> str | None:
    """Read a provider's API key from the OS keychain, if configured."""
    return keyring.get_password(KEYRING_SERVICE, provider_id)


def is_configured(provider: ProviderSpec) -> bool:
    """Whether a provider is ready to use (no key needed, or one is stored)."""
    return not provider.requires_api_key or get_api_key(provider.id) is not None


def list_models(provider_id: str) -> list[str]:
    """List available model ids for a configured provider. Ollama is queried live (it's a local server)."""
    provider = get_provider(provider_id)
    if provider.id == "ollama":
        response = httpx.get(f"{provider.base_url}/api/tags", timeout=5)
        response.raise_for_status()
        return [model["name"] for model in response.json()["models"]]

    if get_api_key(provider.id) is None:
        raise ValueError(f"No API key stored for provider {provider.id!r}; run /login {provider.id} first.")
    return MODELS_SNAPSHOT.get(provider.id, [])
