"""Supply-chain guards for scripts/bootstrap.sh.

The bootstrap is the first thing a broken Mac runs; its failure modes
are the platform's. The script must pin the installer by version AND
content hash, must never touch private key material, must never name
machine-specific paths, and must never say "latest".
"""

import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap.sh"


def test_installer_url_is_version_and_content_pinned():
    text = SCRIPT.read_text()
    version = re.search(r'NIX_INSTALLER_VERSION="(v[0-9]+\.[0-9]+\.[0-9]+)"', text)
    assert version, "NIX_INSTALLER_VERSION constant missing or not semver"
    assert (
        "NIX_INSTALLER_VERSION}" in text.split("INSTALLER_URL=")[1].split("\n")[0]
    ), "installer URL must embed the pinned version constant"
    digest = re.search(r'EXPECTED_INSTALLER_SHA256="([0-9a-f]{64})"', text)
    assert digest, "EXPECTED_INSTALLER_SHA256 content pin missing"


def test_no_sops_decrypt_anywhere():
    assert not re.search(r"\bsops\b.*\s-d\b|--decrypt", SCRIPT.read_text())


def test_no_users_path_literals():
    assert "/Users/" not in SCRIPT.read_text()


def test_no_latest_anywhere():
    assert "latest" not in SCRIPT.read_text().lower()


def test_script_passes_bash_syntax_check():
    r = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# ---- converge + firmlink + age-key guards (dry-gate rebuild rulings) ----


def test_converge_switch_is_root_only():
    """KNOWN GAP 1: activation is root-only on nix-darwin 26.11 (ADR-0005)
    - no bare switch line; sudo "$NIX_BIN" path (plus the EUID==0
    direct-exec branch)."""
    lines = SCRIPT.read_text().splitlines()
    bare = [
        ln
        for ln in lines
        if "run nix-darwin -- switch" in ln
        and "sudo" not in ln
        and "$NIX_BIN" not in ln
        and not ln.lstrip().startswith("#")
    ]
    assert bare == [], f"bare (non-root-only) switch lines: {bare}"
    assert any('sudo "$NIX_BIN" run nix-darwin -- switch' in ln for ln in lines)


def test_converge_runs_dry_build_gate_first():
    """README GitOps loop: dry build before every switch."""
    text = SCRIPT.read_text()
    build_idx = text.find("run nix-darwin -- build --flake")
    switch_idx = text.find("switch --flake")
    assert build_idx != -1 and switch_idx != -1
    assert build_idx < switch_idx


def test_run_firmlink_gate_present():
    text = SCRIPT.read_text()
    bslash_t = "run" + chr(92) + "tprivate/var/run"  # bash $\'...\' literal \t in source
    assert bslash_t in text  # literal-TAB BSD-grep pattern
    assert "grep -qxF 'nix'" in text  # exact-line nix entry check
    assert "ls -A /run" in text  # stale bare-directory check


def test_synthetic_conf_is_never_mutated():
    """No executable line may write /etc/synthetic.conf or reboot. The
    die() message legitimately embeds the repair commands - treat the
    whole message (including multi-line continuations inside the open
    double-quoted die/log/echo string) as text."""
    lines = SCRIPT.read_text().splitlines()
    in_message = False
    violations = []
    for i, ln in enumerate(lines, 1):
        stripped = ln.strip()
        if re.match(r'^(die|log|echo)\s+"', stripped):
            in_message = True
        if in_message:
            # a double-quoted bash string ends on an unescaped '"'
            if stripped.endswith('"') and not stripped.endswith('\\"'):
                in_message = False
            continue
        if stripped.startswith("#"):
            continue
        if "reboot" in ln:
            violations.append(f"line {i}: reboot outside message")
        if "/etc/synthetic.conf" in ln and (">" in ln or " tee " in ln or "dd " in ln):
            violations.append(f"line {i}: synthetic.conf write outside message")
    assert violations == [], violations


def test_age_key_check_covers_all_nix_modules():
    text = SCRIPT.read_text()
    assert "nix/flake.nix" in text and "nix/inference.nix" in text
    sops_grep_lines = [ln for ln in text.splitlines() if "sops" in ln and "secrets" in ln]
    assert any("nix/flake.nix" in ln for ln in sops_grep_lines)
    assert any("nix/inference.nix" in ln for ln in sops_grep_lines)
