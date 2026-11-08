"""The pinned GGUF manifest must parse with the expected table shape.

models/models.toml is the source of truth for scripts/sync-models.sh:
download -> verify -> generate swap config. A malformed or wrongly-shaped
manifest must fail here, not on the Mac mid-download.

The pin guard below makes a forgotten pin fail here, not on the Mac
mid-download: every entry must carry a 40-hex rev and a 64-hex sha256.
"""

import re
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


def test_every_model_pin_is_resolved():
    """A forgotten pin must fail the gate here, not on the Mac mid-download.

    rev: 40-hex git sha; sha256: 64-hex digest. fullmatch makes a TODO
    placeholder structurally impossible to pass.
    """
    bad = []
    for entry in tomllib.loads(MANIFEST.read_text())["models"]:
        if not re.fullmatch(r"[0-9a-f]{40}", entry["rev"]) or not re.fullmatch(
            r"[0-9a-f]{64}", entry["sha256"]
        ):
            bad.append(entry["name"])
    assert bad == []


def test_every_entry_has_dest_matching_swap_cmd():
    """sync-models (roadmap PR 4) downloads `file`, saves as `dest`.

    The swap cmd must reference dest - the local name - never the
    upstream file name, so the two may differ freely upstream.
    """
    bad = []
    for entry in tomllib.loads(MANIFEST.read_text())["models"]:
        dest = entry.get("dest", "")
        if not dest or dest not in entry["swap"]["cmd"]:
            bad.append(entry["name"])
    assert bad == []


def test_isolated_entries_have_port_others_keep_port_macro():
    """Isolated tiers run OUTSIDE the swap matrix on a fixed port;
    matrix tiers get ${PORT} substituted by llama-swap per spawn."""
    bad = []
    for entry in tomllib.loads(MANIFEST.read_text())["models"]:
        isolated = entry.get("isolated", False)
        if isolated and not isinstance(entry.get("port"), int):
            bad.append(entry["name"])
        if not isolated and "${PORT}" not in entry["swap"]["cmd"]:
            bad.append(entry["name"])
    assert bad == []
