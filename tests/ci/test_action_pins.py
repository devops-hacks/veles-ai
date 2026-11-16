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

USES_RE = re.compile(r"^\s*-? ?uses:\s*([^\s@]+)(@\S+)?\s*(?:#.*)?$", re.MULTILINE)

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


def test_uses_regex_captures_ref_on_commented_line():
    """RED-first: the old regex matched no commented uses: line at all."""
    line = (
        "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
        "  # v4, full-SHA pin\n"
    )
    m = USES_RE.search(line)
    assert m is not None, "regex must match a uses: line with a trailing comment"
    assert m.group(1) == "actions/checkout"
    assert m.group(2) == "@11d5960a326750d5838078e36cf38b85af677262"


def test_every_uses_line_in_ci_is_actually_matched():
    """Guard anti-vacuity: every uses: occurrence in ci.yml is parsed."""
    text = CI.read_text()
    occurrences = len(re.findall(r"^\s*-? ?uses:", text, re.MULTILINE))
    matches = len(USES_RE.findall(text))
    assert occurrences > 0
    assert matches == occurrences, (
        f"pins guard matched {matches} of {occurrences} uses: lines - "
        "a floating ref on an unmatched line would pass silently"
    )
