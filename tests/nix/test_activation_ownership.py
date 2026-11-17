"""Activation must enforce model-volume ownership and provision the
sync-models log home - via a WIRED nix-darwin chunk name.

Byte-verified root cause (nix-darwin bb0b90d): activation-scripts.nix
assembles `activate` from an ENUMERATED list of chunk names only
(preActivation, checks, ..., postActivation). Custom
system.activationScripts names are silently dead code - the PR #27
chunks (llamaModelsVolume, velesLogDir) and PR #29 commit 1
(veles-ownership) never ran for exactly this reason. The cure must be
contributed to the wired `postActivation` name via types.lines
concatenation (the pattern nix-darwin's own modules use).

Contract: root context, NON-FATAL (every failure emits grep-able
MARKER-A2 and continues; zero bare failing commands under set -e),
exactly two MARKER-A2 emission points (log home, gguf), the success
line carries the runbook grep contract, and no silent `|| true`
swallows anywhere.
"""

import re
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "nix" / "inference.nix"
SYNC = Path(__file__).resolve().parents[2] / "scripts" / "sync-models.sh"

# the wired chunk names nix-darwin bb0b90d actually interpolates into
# `activate` (modules/system/activation-scripts.nix, enumerated list)
WIRED_CHUNKS = {
    "preActivation",
    "checks",
    "createRun",
    "extraActivation",
    "groups",
    "users",
    "applications",
    "pam",
    "patches",
    "openssh",
    "etc",
    "defaults",
    "userDefaults",
    "launchd",
    "userLaunchd",
    "nix-daemon",
    "time",
    "networking",
    "power",
    "keyboard",
    "fonts",
    "nvram",
    "mas",
    "homebrew",
    "postActivation",
}


def post_activation_text():
    m = re.search(
        r"system\.activationScripts\.postActivation\.text\s*=\s*''(.*?)'';",
        MODULE.read_text(),
        re.DOTALL,
    )
    return m.group(1) if m else ""


def test_ownership_cure_is_contributed_to_the_wired_postactivation_chunk():
    text = post_activation_text()
    assert text, (
        "ownership cure must be contributed to the WIRED postActivation "
        "chunk - custom system.activationScripts names are dead code in "
        "nix-darwin bb0b90d"
    )
    assert "/var/log/veles" in text
    assert "model volume ownership verified" in text, "runbook grep contract"
    assert text.count("MARKER-A2") == 2, f"MARKER-A2 count: {text.count('MARKER-A2')}"


def test_activation_chunk_is_nonfatal_and_idempotent():
    text = post_activation_text()
    assert "exit 1" not in text, "a failed chown must never abort a switch"
    assert "|| true" not in text, "silent failure swallow is the anomaly-2 regression"
    assert "mkdir -p" in text, "idempotent provisioning"
    # exactly two enforcement chowns (log-home files + gguf dir)
    assert len(re.findall(r"chown (?:-R )?_veles:_veles", text)) == 2


def test_every_declared_activation_chunk_name_is_wired():
    """Class-closure: a custom chunk name = silent dead code = this test
    fails the PR before it can ship."""
    declared = set(re.findall(r"system\.activationScripts\.([A-Za-z0-9_-]+)", MODULE.read_text()))
    unwired = sorted(declared - WIRED_CHUNKS)
    assert unwired == [], f"unwired activation chunk names: {unwired}"


def test_sync_models_fails_loud_on_unwritable_root():
    assert "MODELS_ROOT not writable by" in SYNC.read_text()
