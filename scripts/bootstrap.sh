#!/usr/bin/env bash
# scripts/bootstrap.sh - reproducible bring-up: bare arm64 macOS -> converged darwin config (1b-ii)
#
# Usage:
#   scripts/bootstrap.sh           # apply mode: install, converge, verify
#   scripts/bootstrap.sh --check   # verify-only: no mutation, no downloads
#
# Trust anchor for the Nix installer:
#   - Pinned by VERSION  (NIX_INSTALLER_VERSION below) AND content hash
#     (EXPECTED_INSTALLER_SHA256 below, taken from the GitHub release
#     asset digest via the API at authoring time).
#   - Fetched over HTTPS from github.com release assets - NEVER via a
#     "pipe to shell" one-liner, which is unverifiable by construction.
#   - Upstream publishes no per-version checksums file for release
#     assets; the in-repo content hash below is the verification.
#   - Changing either constant is a reviewed PR, never an in-place edit.
#
# Identity (age key, Tailscale) is OPERATOR-HANDLED by design: this
# script verifies presence and prints instructions; it never creates,
# moves, decrypts, or authenticates anything secret.
#
# Modes are idempotent: every step detects existing state first.

set -euo pipefail

# ---- pinned constants (change only via reviewed PR) ----
readonly NIX_INSTALLER_VERSION="v3.24.1"
readonly INSTALLER_URL="https://github.com/DeterminateSystems/nix-installer/releases/download/${NIX_INSTALLER_VERSION}/nix-installer-aarch64-darwin"
readonly EXPECTED_INSTALLER_SHA256="34199f983d1a08e76a4fb33b28691faa637fc4a8677b4de20bd951126e1bdada"
readonly CANONICAL_REPO_URL="https://github.com/devops-hacks/veles-ai.git"
readonly HOST_FLAKE_REF="mac-ai"
readonly AGE_KEY_PATH="${HOME}/Library/Application Support/sops/age/keys.txt"

MODE="apply"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
elif [[ "${1:-}" != "" ]]; then
  echo "usage: $0 [--check]" >&2
  exit 2
fi

log() { echo "[bootstrap] $*"; }
die() { echo "[bootstrap] FAIL: $*" >&2; exit 1; }

# ---- step a: preflight ----
[[ "$(uname -s)" == "Darwin" ]] || die "preflight: macOS required (got $(uname -s))"
[[ "$(uname -m)" == "arm64" ]] || die "preflight: arm64 required (got $(uname -m))"
xcode-select -p >/dev/null 2>&1 || die "preflight: Xcode CLT missing - run: xcode-select --install"
command -v git >/dev/null 2>&1 || die "preflight: git missing"
log "preflight: darwin/arm64, Xcode CLT, git OK"

# ---- step b: nix (pinned installer, content-verified) ----
nix_on_path() { command -v nix >/dev/null 2>&1; }

if ! nix_on_path && [[ -x /nix/var/nix/profiles/default/bin/nix ]]; then
  # Non-interactive shells do not source /etc/profile.d; wire it in.
  # shellcheck disable=SC1091
  source /etc/profile.d/nix.sh
fi

if nix_on_path; then
  log "nix: present ($(nix --version 2>/dev/null | head -1))"
else
  if [[ "$MODE" == "check" ]]; then
    log "nix: ABSENT - check mode stops here (apply mode would run the pinned ${NIX_INSTALLER_VERSION} installer)"
    exit 1
  fi
  log "nix: absent - downloading pinned installer ${NIX_INSTALLER_VERSION}"
  TMPDIR_BOOT="$(mktemp -d)"
  trap 'rm -rf "$TMPDIR_BOOT"' EXIT
  curl --fail --proto '=https' --tlsv1.2 --silent --show-error --location \
    -o "${TMPDIR_BOOT}/nix-installer" "$INSTALLER_URL"
  echo "${EXPECTED_INSTALLER_SHA256}  ${TMPDIR_BOOT}/nix-installer" | shasum -a 256 --check -
  chmod +x "${TMPDIR_BOOT}/nix-installer"
  log "nix: installer hash verified - running install (sudo prompt expected)"
  "${TMPDIR_BOOT}/nix-installer" install
  # shellcheck disable=SC1091
  source /etc/profile.d/nix.sh
  nix_on_path || die "nix: still not on PATH after install"
  log "nix: installed $(nix --version 2>/dev/null | head -1)"
fi

# ---- step c: repo (this checkout must be the converged truth) ----
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  # Standalone copy of the script: clone from the canonical URL.
  if [[ "$MODE" == "check" ]]; then
    die "repo: no checkout found - apply mode would clone ${CANONICAL_REPO_URL} to \${HOME}/veles-ai"
  fi
  log "repo: no checkout found - cloning from the canonical URL"
  git clone --quiet "$CANONICAL_REPO_URL" "${HOME}/veles-ai" \
    || die "repo: clone failed (private repo - authenticate first)"
  REPO_ROOT="${HOME}/veles-ai"
fi
if [[ "$MODE" == "apply" ]]; then
  git -C "$REPO_ROOT" fetch origin main --quiet
fi
HEAD_REV="$(git -C "$REPO_ROOT" rev-parse HEAD)"
MAIN_REV="$(git -C "$REPO_ROOT" rev-parse origin/main 2>/dev/null || echo "unknown")"
[[ "$MAIN_REV" == "$HEAD_REV" ]] || die "repo: HEAD ${HEAD_REV:0:7} != origin/main ${MAIN_REV:0:7} - pull first (apply mode already fetched; check mode uses the last fetch)"
if [[ "$MODE" == "apply" ]] && [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  die "repo: working tree dirty - converge runs the declared state, commit or stash first"
fi
log "repo: $REPO_ROOT at ${HEAD_REV:0:7} matches origin/main"

# ---- step d: converge (the proven 1b-i command; NEVER update the lock here) ----
if [[ "$MODE" == "apply" ]]; then
  log "converge: darwin switch for .#${HOST_FLAKE_REF} (reviewed lock only - this script never runs flake update)"
  nix run nix-darwin -- switch --flake "${REPO_ROOT}/nix#${HOST_FLAKE_REF}"
  log "converge: switch complete"
else
  nix flake check --no-build "${REPO_ROOT}/nix"
  log "converge: flake evaluates (check mode does not switch)"
fi

# ---- step e: identity (operator-handled; verify + instruct, never act) ----
OUTSTANDING=0

if grep -Eq '^[^#]*sops\.secrets\.' "${REPO_ROOT}/nix/flake.nix"; then
  if [[ -f "$AGE_KEY_PATH" ]]; then
    log "identity: age key present at the configured path"
  else
    if [[ "$MODE" == "apply" ]]; then
      die "identity: sops.secrets are defined but no age key at: ${AGE_KEY_PATH}
  operator action (never scripted):
    mkdir -p \"\${HOME}/Library/Application Support/sops/age\"
    age-keygen -o \"\${HOME}/Library/Application Support/sops/age/keys.txt\"
    chmod 600 \"\${HOME}/Library/Application Support/sops/age/keys.txt\""
    fi
    log "identity: sops.secrets defined and age key ABSENT (apply mode would stop)"
    OUTSTANDING=1
  fi
else
  log "identity: no sops.secrets defined yet - age key check skipped"
fi

if command -v tailscale >/dev/null 2>&1; then
  log "identity: tailscale present (join/auth status is operator-verified)"
else
  log "identity: WARNING tailscale absent - install + join is an operator action:"
  echo "    install the Tailscale app (or: brew install --cask tailscale), sign in, then:"
  echo "    tailscale up   # then verify ACL reachability per docs/security.md"
  OUTSTANDING=1
fi

if [[ "$MODE" == "apply" ]]; then
  log "apply complete - see docs/bootstrap.md for the operator checklist"
else
  log "check complete (no mutation performed)"
fi
exit "$OUTSTANDING"
