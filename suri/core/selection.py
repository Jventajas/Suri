"""Persisted provider/model selection: survives across restarts.

Saved as a plain JSON file, as it is not a secret. Written atomically and validated on
read, so a corrupt file or a since-invalidated provider/key falls back to onboarding
instead of crashing the app.
"""

import json
from pathlib import Path

from suri.core.providers import get_provider, is_configured

SELECTION_PATH = Path.home() / ".suri" / "selection.json"


def save_selection(provider_id: str, model_id: str) -> None:
    """Persist the chosen provider/model so onboarding isn't repeated next launch."""
    SELECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SELECTION_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps({"provider_id": provider_id, "model_id": model_id}))
    tmp_path.replace(SELECTION_PATH)


def load_selection() -> tuple[str, str] | None:
    """Return the last persisted (provider_id, model_id), or None if unset or no longer valid."""
    if not SELECTION_PATH.exists():
        return None
    try:
        data = json.loads(SELECTION_PATH.read_text())
        provider_id, model_id = data["provider_id"], data["model_id"]
        provider = get_provider(provider_id)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None
    if not is_configured(provider):
        return None
    return provider_id, model_id
