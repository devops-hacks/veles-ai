"""Contract tests for scripts/check_sops_header.py - the plaintext guard.

Nothing under secrets/ may ever land in git without sops metadata: a
top-level "sops:" key is the proof of encryption. The guard fails the
pre-commit run naming every offending file, so plaintext under secrets/
is structurally impossible to commit.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_sops_header.py"

spec = importlib.util.spec_from_file_location("check_sops_header", SCRIPT)
check_sops_header = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_sops_header)


def run(*args):
    """Invoke the guard like pre-commit does: repo-relative paths, cwd=root."""
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def write(tmp_path, monkeypatch, rel, body):
    """Create the file and chdir so `rel` is the path the script sees."""
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)
    monkeypatch.chdir(tmp_path)
    return rel


def test_no_arguments_exits_zero():
    assert run().returncode == 0


def test_encrypted_file_under_secrets_passes(tmp_path, monkeypatch):
    rel = write(
        tmp_path,
        monkeypatch,
        "secrets/huggingface.yaml",
        "huggingface_token: REDACTED\nsops:\n    age: enc\n",
    )
    assert run(rel).returncode == 0


def test_plaintext_under_secrets_fails_and_names_the_file(tmp_path, monkeypatch):
    rel = write(
        tmp_path,
        monkeypatch,
        "secrets/huggingface.yaml",
        "huggingface_token: REPLACE-ME\n",
    )
    r = run(rel)
    assert r.returncode == 1
    assert rel in r.stdout + r.stderr


def test_all_offenders_are_named(tmp_path, monkeypatch):
    bad1 = write(tmp_path, monkeypatch, "secrets/a.yaml", "token: x\n")
    bad2 = write(tmp_path, monkeypatch, "secrets/b.yml", "token: y\n")
    good = write(tmp_path, monkeypatch, "secrets/c.yaml", "x: 1\nsops:\n    age: enc\n")
    r = run(bad1, good, bad2)
    assert r.returncode == 1
    out = r.stdout + r.stderr
    assert bad1 in out and bad2 in out
    assert good not in out


def test_paths_outside_secrets_are_ignored(tmp_path, monkeypatch):
    rel = write(tmp_path, monkeypatch, "services/compose/whatever.yaml", "image: x\n")
    assert run(rel).returncode == 0


def test_non_yaml_under_secrets_is_ignored(tmp_path, monkeypatch):
    rel = write(tmp_path, monkeypatch, "secrets/notes.txt", "not yaml\n")
    assert run(rel).returncode == 0


def test_indented_or_prefixed_sops_key_is_not_proof(tmp_path, monkeypatch):
    rel = write(
        tmp_path,
        monkeypatch,
        "secrets/tricky.yaml",
        "metadata:\n    sops: not-a-top-level-key\nsopsx: 1\n",
    )
    r = run(rel)
    assert r.returncode == 1
    assert rel in r.stdout + r.stderr
