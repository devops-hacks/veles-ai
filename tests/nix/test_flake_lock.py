"""The flake is declarative truth only when its inputs are pinned.

flake.lock is the system's version pin (Ch. 8): every input the flake
declares must be resolved in the lock, every locked revision must be a
full 40-hex git sha, and no kit placeholder may survive in flake.nix.
A missing or half-pinned lock must fail here, not on the next switch.
"""

import json
import re
from pathlib import Path

NIX = Path(__file__).resolve().parents[2] / "nix"
FLAKE = NIX / "flake.nix"
LOCK = NIX / "flake.lock"

FLAKE_INPUT_RE = re.compile(r'^\s*([A-Za-z0-9_-]+)\.url\s*=\s*"')


def test_flake_lock_exists():
    assert LOCK.is_file()


def test_every_flake_input_is_pinned():
    declared = {
        m.group(1) for line in FLAKE.read_text().splitlines() if (m := FLAKE_INPUT_RE.match(line))
    }
    lock = json.loads(LOCK.read_text())
    resolved = set(lock["nodes"]["root"]["inputs"])
    assert declared <= resolved, f"unlocked inputs: {sorted(declared - resolved)}"

    offenders = []
    for name, node in lock["nodes"].items():
        if name == "root":
            continue
        locked = node.get("locked")
        if locked and not re.fullmatch(r"[0-9a-f]{40}", locked.get("rev", "")):
            offenders.append(f"{name}: {locked.get('rev')!r}")
    assert offenders == []


def test_no_placeholder_tokens_in_flake():
    leftovers = re.findall(r"<[a-z][a-z0-9-]*>", FLAKE.read_text())
    assert leftovers == []
