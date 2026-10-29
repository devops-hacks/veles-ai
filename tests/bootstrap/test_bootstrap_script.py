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
