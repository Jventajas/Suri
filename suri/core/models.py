"""Model provider layer: the hot-swap seam between core and any LLM provider."""

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from suri.core.providers import get_api_key, get_provider


def build_model(provider_id: str, model_id: str) -> BaseChatModel:
    """Return the chat model behind the provider-agnostic interface.

    Both `provider_id` and `model_id` must already be resolved by the caller (onboarding
    or a provider/model switch) — this function never picks a default.
    """
    provider = get_provider(provider_id)

    if provider_id == "ollama":
        return ChatOllama(model=model_id, base_url=provider.base_url)

    api_key = get_api_key(provider_id)
    if api_key is None:
        raise ValueError(f"No API key stored for provider {provider_id!r}; run /login {provider_id} first.")
    return ChatOpenAI(model=model_id, base_url=provider.base_url, api_key=SecretStr(api_key))
