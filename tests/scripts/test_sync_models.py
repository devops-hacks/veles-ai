"""Supply-chain guards for scripts/sync-models.sh (roadmap PR 4).

The downloader is the only code path that pulls bytes from the network
onto the model volume; every fetch is pinned by repo+rev+file and
verified in-repo by sha256, failures are loud, and the script stays
dependency-free (curl + shasum + stdlib python3).
"""

import os
import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sync-models.sh"

FIXTURE_MANIFEST = (
    "[[models]]\n"
    'name = "fixture"\n'
    'repo = "org/repo"\n'
    'rev  = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n'
    'file = "m.gguf"\n'
    'dest = "fixture.gguf"\n'
    'sha256 = "' + "b" * 64 + '"\n'
    "[models.swap]\n"
    'cmd = "llama-server -m fixture.gguf --port ${PORT}"\n'
)


def test_script_passes_bash_syntax_check():
    r = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_no_latest_anywhere():
    assert "latest" not in SCRIPT.read_text().lower()


def test_no_users_path_literals():
    assert "/Users/" not in SCRIPT.read_text()


def test_no_sops_decrypt_anywhere():
    assert not re.search(r"\bsops\b.*\s-d\b|--decrypt", SCRIPT.read_text())


def test_fetch_url_is_repo_rev_file_pinned():
    text = SCRIPT.read_text()
    assert 'HF_BASE="${HF_BASE:-https://huggingface.co}"' in text
    assert "resolve/$rev/$file" in text, "fetch URL must be repo+rev+file pinned"


def test_verify_then_rename_ordering():
    text = SCRIPT.read_text()
    assert "shasum -a 256" in text
    assert text.index("sha256 mismatch") < text.index(
        'mv "$tmp" "$out"'
    ), "the .part temp must be renamed into place only after verification"


def test_dry_run_prints_pinned_urls(tmp_path):
    manifest = tmp_path / "models.toml"
    manifest.write_text(FIXTURE_MANIFEST)
    root = tmp_path / "gguf"
    root.mkdir()
    r = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "MODELS_ROOT": str(root),
            "MANIFEST": str(manifest),
            "SYNC_PYTHON": "python3",
        },
    )
    assert r.returncode == 0, r.stderr
    assert (
        "https://huggingface.co/org/repo/resolve/"
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/m.gguf" in r.stdout
    ), r.stdout


def test_curl_aborts_stalled_transfers():
    """2026-11-18 evidence: a silently stalled connection sat at 8.0G for
    hours - --retry does not fire on a stall (no error), so the transfer
    hung until a manual kickstart -k. --speed-limit/--speed-time turn the
    stall into a curl error (exit 28), which --retry treats as transient:
    self-abort, auto-resume via -C -, die loud only after retries exhaust."""
    text = SCRIPT.read_text()
    line = next(ln for ln in text.splitlines() if ln.lstrip().startswith("curl "))
    assert line.strip() == (
        "curl -fL -C - --retry 3 --retry-delay 5 "
        '--speed-limit 1024 --speed-time 60 -o "$tmp" "$url" \\'
    ), f"curl invocation drifted: {line.strip()!r}"
