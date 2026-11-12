"""Source guards for the inference core (nix/inference.nix + flake).

These encode the invariants the review must not have to re-argue:
loopback-only binds, no operator username, least-privilege service
account, pinned binary, sops-managed keys, and the primaryUser trap
kept shut (system daemons only, never launchd.user.services).
"""

import re
from pathlib import Path

NIX = Path(__file__).resolve().parents[2] / "nix"
FLAKE = (NIX / "flake.nix").read_text()
MODULE = NIX / "inference.nix"
MODULE_TEXT = MODULE.read_text() if MODULE.is_file() else ""
NIX_FILES = {p: p.read_text() for p in NIX.glob("*.nix")}

SOPS_SECRETS = ["llama_swap/key_operator", "llama_swap/key_family", "llama_swap/key_agents"]

# /Users/<anything> is forbidden except /Users/Shared/... (no real usernames,
# including in this test - the lookahead names no one)
USERS_PATH_RE = re.compile(r"/Users/(?!Shared/)[A-Za-z0-9_-]+")


def test_loopback_bind_only():
    text = FLAKE + MODULE_TEXT
    assert "-listen 127.0.0.1:4002" in text
    for path, src in NIX_FILES.items():
        assert "0.0.0.0" not in src, f"wildcard bind in {path.name}"


def test_no_users_paths_outside_shared():
    for path, src in NIX_FILES.items():
        assert not USERS_PATH_RE.search(src), f"/Users/<name> path in {path.name}"


def test_three_sops_secrets_owner_and_mode():
    for secret in SOPS_SECRETS:
        block_re = re.compile(
            r'sops\.secrets\."' + re.escape(secret) + r'"\s*=\s*\{(.*?)\};', re.DOTALL
        )
        m = block_re.search(MODULE_TEXT)
        assert m, f"missing sops.secrets.{secret}"
        block = m.group(1)
        assert 'owner = "_veles"' in block, secret
        assert 'mode = "0400"' in block, secret


def test_services_run_as_service_account():
    assert MODULE_TEXT.count('UserName = "_veles";') == 2


def test_binary_pinned_no_floating_refs():
    # bare number: the v prefix lives in the URL path segment, not the
    # constant (the v268 filename form 404s - release assets are unversioned)
    assert re.search(r'LLAMA_SWAP_VERSION\s*=\s*"\d+"', MODULE_TEXT)
    # SRI form (sha256-<base64>) - what fetchurl consumes and the release
    # asset API publishes; bootstrap.sh keeps the same content-pin discipline
    assert re.search(r'LLAMA_SWAP_SHA256\s*=\s*"sha256-[A-Za-z0-9+/=]{40,}"', MODULE_TEXT)
    for path, src in NIX_FILES.items():
        assert "latest" not in src.lower(), f"floating ref in {path.name}"


def test_no_user_launchd_services():
    for path, src in NIX_FILES.items():
        assert (
            "launchd.user.services" not in src
        ), f"launchd.user.services in {path.name} - primaryUser trap"


def test_module_declares_no_users_entries():
    """Pattern (b), architect-approved on the probe data: nix-darwin's
    users.users declaration x launchd UserName recurses at the pinned
    revs, so the module declares NO users.* entries - the hidden
    service account is operator-created (docs/inference.md).
    """
    for declaration in ("users.users", "users.knownUsers", "users.groups"):
        assert declaration not in MODULE_TEXT, declaration
