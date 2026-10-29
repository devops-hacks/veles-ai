"""Every GitHub Action ref must be pinned to a full 40-hex commit SHA.

A floating tag (v4, v23) is mutable: the code it names can change under
a merged PR - the supply-chain hole of threat actor "supply chain"
(doc Ch. 15). The nix-installer-action precedent (PR 9) applies
repo-wide: no floating refs in ci.yml, full SHAs only.
"""

import re
from pathlib import Path

CI = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
PRECOMMIT = Path(__file__).resolve().parents[2] / ".pre-commit-config.yaml"

USES_RE = re.compile(r"^\s*-? ?uses:\s*(\S+)\s*(@\S+)?\s*$", re.MULTILINE)

# local hooks (repo: local) have no rev by design; everything upstream must pin
REV_RE = re.compile(r"^\s*rev:\s*(\S+)\s*$", re.MULTILINE)


def test_every_precommit_hook_rev_is_fully_pinned():
    offenders = []
    for m in REV_RE.finditer(PRECOMMIT.read_text()):
        rev = m.group(1)
        if not re.fullmatch(r"[0-9a-f]{40}", rev):
            offenders.append(rev)
    assert offenders == [], f"floating hook revs in .pre-commit-config.yaml: {offenders}"


def test_every_action_ref_is_fully_pinned():
    offenders = []
    for m in USES_RE.finditer(CI.read_text()):
        ref = m.group(2).lstrip("@") if m.group(2) else ""
        if not re.fullmatch(r"[0-9a-f]{40}", ref):
            offenders.append(f"{m.group(1)} (ref: {ref or 'none'!r})")
    assert offenders == [], f"floating action refs in ci.yml: {offenders}"
