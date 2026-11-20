#!/usr/bin/env bash
# scripts/sync-models.sh - manifest -> download -> verify (roadmap PR 4).
#
# Division of labor (recorded ruling): the swap config is NIX-BUILT
# (nix/inference.nix runs scripts/generate_swap_config.py at build time);
# this script does NOT regenerate or reload it. Its whole job: fetch each
# pinned GGUF into MODELS_ROOT, verify sha256 against the manifest, stay
# idempotent, fail loud. Transport is curl against the pinned resolve URL
# (repo+rev+file); integrity comes from the in-repo sha256 pin, not from
# the transport. No tokens: both pinned repos are public;
# secrets/huggingface.yaml stays reserved for a future ruling.
#
# Exit contract: absent volume or failed fetch => non-zero, ONCE (the
# launchd timer has no KeepAlive - no crash loop, loud .err log).
set -euo pipefail

MODELS_ROOT="${MODELS_ROOT:-/Volumes/ai-models/gguf}"
MANIFEST="${MANIFEST:-$(cd "$(dirname "$0")/.." && pwd)/models/models.toml}"
SYNC_PYTHON="${SYNC_PYTHON:-python3}"
HF_BASE="${HF_BASE:-https://huggingface.co}"

DRY_RUN=0
PRUNE=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=1 ;;
    --prune)   PRUNE=1 ;;
    *) printf '[sync-models] FAIL: unknown arg %s\n' "$a" >&2; exit 2 ;;
  esac
done

log() { printf '[sync-models] %s\n' "$*"; }
die() { printf '[sync-models] FAIL: %s\n' "$*" >&2; exit 1; }

[ -f "$MANIFEST" ] || die "manifest missing: $MANIFEST"
[ -d "$MODELS_ROOT" ] || die "MODELS_ROOT absent: $MODELS_ROOT (volume not mounted - stay-down contract applies; fix the mount, re-run)"
[ -w "$MODELS_ROOT" ] || die "MODELS_ROOT not writable by $(id -un) (expects activation chown; see runbook step 1)"

# manifest -> TSV rows: repo|rev|file|dest|sha256 (stdlib tomllib)
ROWS="$("$SYNC_PYTHON" - "$MANIFEST" <<'PYEOF'
import sys, tomllib

entries = tomllib.loads(open(sys.argv[1], encoding="utf-8").read()).get("models", [])
if not entries:
    sys.exit("manifest has no [[models]] entries")
for e in entries:
    for k in ("repo", "rev", "file", "dest", "sha256"):
        if not e.get(k):
            sys.exit(f"entry {e.get('name', '?')!r} missing pin field {k!r}")
    print("|".join([e["repo"], e["rev"], e["file"], e["dest"], e["sha256"]]))
PYEOF
)" || die "manifest parse failed (see stderr above)"
[ -n "$ROWS" ] || die "manifest yielded zero entries"

fetch_one() {
  repo="$1"; rev="$2"; file="$3"; dest="$4"; want="$5"
  out="$MODELS_ROOT/$dest"
  url="$HF_BASE/$repo/resolve/$rev/$file"
  if [ -f "$out" ]; then
    got="$(shasum -a 256 "$out" | awk '{print $1}')"
    if [ "$got" = "$want" ]; then
      log "OK (cached, hash verified) $dest"
      return 0
    fi
    log "existing $dest fails sha256 - refetching"
  fi
  if [ "$DRY_RUN" = 1 ]; then
    log "dry-run: would fetch $dest from $url"
    return 0
  fi
  tmp="$out.part"
  log "fetch $dest"
  log "  url: $url"
  curl -fL -C - --retry 3 --retry-delay 5 --speed-limit 1024 --speed-time 60 -o "$tmp" "$url" \
    || die "curl failed for $dest ($url)"
  got="$(shasum -a 256 "$tmp" | awk '{print $1}')"
  if [ "$got" != "$want" ]; then
    rm -f "$tmp"
    die "sha256 mismatch for $dest: got $got, manifest wants $want (temp removed)"
  fi
  mv "$tmp" "$out"
  log "verified $dest  sha256:$want"
}

DESTS="$(printf '%s\n' "$ROWS" | awk -F'|' '{print $4}')"

while IFS='|' read -r repo rev file dest want; do
  fetch_one "$repo" "$rev" "$file" "$dest" "$want"
done < <(printf '%s\n' "$ROWS")

# prune orphans: *.gguf in MODELS_ROOT not named by the manifest (opt-in)
ORPHANS="$(find "$MODELS_ROOT" -maxdepth 1 -name '*.gguf' | while IFS= read -r p; do
  base="$(basename "$p")"
  grep -qxF "$base" <<<"$DESTS" || printf '%s\n' "$base"
done)"
if [ -n "$ORPHANS" ]; then
  if [ "$PRUNE" = 1 ]; then
    printf '%s\n' "$ORPHANS" | while IFS= read -r o; do
      log "prune orphan: $o"
      rm -f "$MODELS_ROOT/$o"
    done
  else
    log "orphans present (pass --prune to remove):"
    printf '%s\n' "$ORPHANS" | sed 's/^/  orphan: /'
  fi
else
  log "no orphans"
fi

log "done"
