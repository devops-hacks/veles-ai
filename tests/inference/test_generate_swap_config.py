"""Contract tests for scripts/generate_swap_config.py.

The generator is the only writer of llama-swap's config: it must emit
the exact A1 shape (three env-macro keys, no literal key material), keep
llama-swap's ${PORT} contract for matrix models, and fail closed naming
the offending manifest entry when the manifest is malformed.
"""

import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "scripts" / "generate_swap_config.py"
MANIFEST = REPO / "models" / "models.toml"

LLAMA_SERVER = "/nix/store/fake-llama-cpp/bin/llama-server"
MODELS_ROOT = "/Volumes/ai-models/gguf"

API_KEYS = [
    "${env.LLAMA_SWAP_KEY_OPERATOR}",
    "${env.LLAMA_SWAP_KEY_FAMILY}",
    "${env.LLAMA_SWAP_KEY_AGENTS}",
]


def run_generator(manifest: Path, out_dir: Path):
    return subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--manifest",
            str(manifest),
            "--llama-server",
            LLAMA_SERVER,
            "--models-root",
            MODELS_ROOT,
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )


def read_manifest():
    return tomllib.loads(MANIFEST.read_text())


def write_fixture(tmp_path, entries, filename="manifest.toml"):
    """Hand-emit a fixture manifest from parsed entry dicts."""
    out = []
    for e in entries:
        swap = e.pop("swap")
        out.append("[[models]]")
        for k, v in e.items():
            if isinstance(v, bool):
                out.append(f"{k} = {'true' if v else 'false'}")
            elif isinstance(v, str):
                out.append(f'{k} = "{v}"')
            else:
                out.append(f"{k} = {v!r}")
        out.append("[models.swap]")
        out.append(f'cmd = "{swap["cmd"]}"')
        out.append("")
    f = tmp_path / filename
    f.write_text("\n".join(out))
    return f


def real_entries():
    """The repo manifest's entries, verbatim (minus swap sub-table)."""
    data = read_manifest()["models"]
    return [{**e, "swap": e["swap"]} for e in data]


def matrix_entry():
    return next(e for e in real_entries() if not e.get("isolated"))


def isolated_entry():
    return next(e for e in real_entries() if e.get("isolated"))


# ---- happy paths ----


def test_generates_config_and_isolated_cmd(tmp_path):
    r = run_generator(MANIFEST, tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "config.yml").is_file()
    iso = [e for e in read_manifest()["models"] if e.get("isolated")]
    for e in iso:
        assert (tmp_path / f"isolated-{e['name']}.cmd").is_file()


def test_matrix_config_shape(tmp_path):
    run_generator(MANIFEST, tmp_path)
    text = (tmp_path / "config.yml").read_text()
    # A1 keys: exactly the three env macros, in order
    keys_lines = [
        ln.strip()[2:].strip('"') for ln in text.splitlines() if ln.strip().startswith("- ")
    ]
    assert keys_lines == API_KEYS
    assert "globalTTL: 1800" in text
    e = matrix_entry()
    assert f'"{e["name"]}":' in text
    assert LLAMA_SERVER in text
    assert "${PORT}" in text  # llama-swap substitutes per spawn
    assert e["dest"] in text  # local dest path, not upstream file
    assert e["file"] not in text  # upstream name must not leak in


def test_isolated_cmd_uses_fixed_port(tmp_path):
    run_generator(MANIFEST, tmp_path)
    e = isolated_entry()
    line = (tmp_path / f"isolated-{e['name']}.cmd").read_text().strip()
    assert str(e["port"]) in line
    assert "${PORT}" not in line
    assert LLAMA_SERVER in line
    assert e["dest"] in line


def test_isolated_cmd_prefixes_models_root_exactly_once(tmp_path):
    run_generator(MANIFEST, tmp_path)
    e = isolated_entry()
    line = (tmp_path / f"isolated-{e['name']}.cmd").read_text()
    assert line.count(MODELS_ROOT) == 1, f"models-root doubled: {line!r}"


def test_exact_model_argument(tmp_path):
    run_generator(MANIFEST, tmp_path)
    e = isolated_entry()
    line = (tmp_path / f"isolated-{e['name']}.cmd").read_text()
    assert f"-m {MODELS_ROOT}/{e['dest']}" in line


def test_matrix_model_argument_single_prefix(tmp_path):
    run_generator(MANIFEST, tmp_path)
    e = matrix_entry()
    text = (tmp_path / "config.yml").read_text()
    assert f"-m {MODELS_ROOT}/{e['dest']}" in text
    assert text.count(MODELS_ROOT) == 1


def test_fail_closed_absolute_model_path(tmp_path):
    e = matrix_entry()
    e["swap"]["cmd"] = e["swap"]["cmd"].replace(f"-m {e['dest']}", f"-m {MODELS_ROOT}/{e['dest']}")
    r = run_generator(write_fixture(tmp_path, mutate(swap=e["swap"])), tmp_path / "o")
    assert r.returncode != 0
    assert e["name"] in r.stderr


def test_fail_closed_wrong_first_token(tmp_path):
    e = matrix_entry()
    e["swap"]["cmd"] = e["swap"]["cmd"].replace("llama-server", "other-server", 1)
    r = run_generator(write_fixture(tmp_path, mutate(swap=e["swap"])), tmp_path / "o")
    assert r.returncode != 0
    assert e["name"] in r.stderr


def test_no_literal_key_material_in_outputs(tmp_path):
    run_generator(MANIFEST, tmp_path)
    for f in tmp_path.iterdir():
        assert "sk-" not in f.read_text(), f.name
        assert "REPLACE-ME" not in f.read_text(), f.name


# ---- fail-closed (mutation matrix) ----


def mutate(**changes):
    e = matrix_entry()
    e.update(changes)
    return [e, isolated_entry()]


def test_fail_closed_cmd_without_dest(tmp_path):
    e = matrix_entry()
    e["swap"]["cmd"] = e["swap"]["cmd"].replace(e["dest"], "wrong-name.gguf")
    r = run_generator(write_fixture(tmp_path, mutate(swap=e["swap"])), tmp_path / "o")
    assert r.returncode != 0
    assert e["name"] in r.stderr


def test_fail_closed_isolated_without_port(tmp_path):
    iso = isolated_entry()
    iso.pop("port")
    r = run_generator(write_fixture(tmp_path, [matrix_entry(), iso]), tmp_path / "o")
    assert r.returncode != 0
    assert iso["name"] in r.stderr


def test_fail_closed_matrix_without_port_macro(tmp_path):
    e = matrix_entry()
    e["swap"]["cmd"] = e["swap"]["cmd"].replace("${PORT}", "8080")
    r = run_generator(write_fixture(tmp_path, mutate(swap=e["swap"])), tmp_path / "o")
    assert r.returncode != 0
    assert e["name"] in r.stderr


def test_fail_closed_missing_pin_field(tmp_path):
    e = matrix_entry()
    e.pop("sha256")
    r = run_generator(write_fixture(tmp_path, [e, isolated_entry()]), tmp_path / "o")
    assert r.returncode != 0
    assert e["name"] in r.stderr
