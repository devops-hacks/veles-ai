"""The pinned GGUF manifest must parse with the expected table shape.

models/models.toml is the source of truth for scripts/sync-models.sh:
download -> verify -> generate swap config. A malformed or wrongly-shaped
manifest must fail here, not on the Mac mid-download.

(PR 1a-2 will add the RED-first guard requiring every entry to carry a
non-TODO rev and a 64-hex sha256 - TODO pins are inert until then.)
"""

import tomllib
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[2] / "models" / "models.toml"


def test_manifest_parses_into_models_tables():
    data = tomllib.loads(MANIFEST.read_text())
    assert isinstance(data["models"], list) and data["models"]


def test_every_model_entry_has_swap_command():
    data = tomllib.loads(MANIFEST.read_text())
    for entry in data["models"]:
        assert entry["name"] and entry["repo"] and entry["file"]
        assert entry["swap"]["cmd"].startswith("llama-server")
