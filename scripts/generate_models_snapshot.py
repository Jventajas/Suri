"""Regenerate suri/core/data/models_snapshot.json from models.dev.

Run manually at release time (`uv run python scripts/generate_models_snapshot.py`)
and commit the result — never fetched at runtime by the app itself.
"""

import json
from pathlib import Path

import httpx

from suri.core.providers import PROVIDERS

MODELS_DEV_URL = "https://models.dev/api.json"
SNAPSHOT_PATH = Path(__file__).parent.parent / "suri" / "core" / "data" / "models_snapshot.json"


def main() -> None:
    response = httpx.get(MODELS_DEV_URL, timeout=10)
    response.raise_for_status()
    catalog = response.json()

    snapshot: dict[str, list[str]] = {}
    for provider in PROVIDERS:
        if provider.id == "ollama":
            continue
        models = catalog.get(provider.id, {}).get("models", {})
        snapshot[provider.id] = sorted(model_id for model_id, model in models.items() if model.get("tool_call"))

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n")
    print(f"Wrote {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
