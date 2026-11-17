"""Activation must enforce model-volume ownership and provision the
sync-models log home - root-context, NON-FATAL (a failed chown must
never abort a switch), loud via grep-able MARKER-A2 lines. Closes the
PROMPT-F ownership-cure gap: the PR #27 audit asserted ledger/scope/
topology but never byte-asserted the ownership contract; this file
closes that class permanently.
"""

import re
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "nix" / "inference.nix"
SYNC = Path(__file__).resolve().parents[2] / "scripts" / "sync-models.sh"


def chunk_text():
    """The veles-ownership activation shell text (between the heredoc
    markers), or '' when the chunk is absent."""
    m = re.search(
        r"veles-ownership\s*=\s*\{.*?text\s*=\s*''(.*?)'';",
        MODULE.read_text(),
        re.DOTALL,
    )
    return m.group(1) if m else ""


def test_activation_chunk_provisions_and_enforces():
    text = chunk_text()
    assert "veles-ownership" in MODULE.read_text(), "activation chunk missing"
    assert "/var/log/veles" in text
    assert "model volume ownership verified" in text, "runbook grep contract"
    # exactly two MARKER-A2 failure lines: log dir + gguf - no others
    assert text.count("MARKER-A2") == 2, f"MARKER-A2 count: {text.count('MARKER-A2')}"
    # exactly two enforcement chowns (the success printf's _veles:_veles
    # mention is documentation, not a chown)
    assert len(re.findall(r"chown _veles:_veles", MODULE.read_text())) == 2
    # dir-only enforcement (the dir is empty; volume root untouched)
    assert "chown -R" not in text


def test_activation_chunk_is_nonfatal_and_idempotent():
    text = chunk_text()
    assert "exit 1" not in text, "a failed chown must never abort a switch"
    assert "mkdir -p" in text, "idempotent provisioning"


def test_sync_models_fails_loud_on_unwritable_root():
    assert "MODELS_ROOT not writable by" in SYNC.read_text()
