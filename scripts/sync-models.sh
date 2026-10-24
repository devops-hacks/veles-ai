#!/usr/bin/env bash
# scripts/sync-models.sh - manifest -> disk -> swap config -> reload (condensed)
# TODO: this skeleton mirrors Appendix A Listing A-3; make it fail loud.
set -euo pipefail

MODELS_ROOT="${MODELS_ROOT:-/Volumes/ai-models/gguf}"
MANIFEST="$(dirname "$0")/../models/models.toml"

# 1) download/verify each pinned file
#    while read -r repo rev file dest; do ... done < <(tomlq -r ...)
echo "TODO: iterate [[model]] entries from $MANIFEST"
#    hf download "$repo" "$file" --revision "$rev" --local-dir "$MODELS_ROOT/$dest"
#    verify_hashes   # check sha256 against manifest; abort on mismatch

# 2) prune orphans not present in the manifest (dry-run first)
#    prune_orphans "$MODELS_ROOT"

# 3) regenerate llama-swap config.yml from [[model.swap]] cmd blocks
#    generate_llama_swap_config > /run/llama-swap/config.yml

# 4) reload the router only if config changed
#    launchctl kickstart -k "gui/$(id -u)/org.nixos.llama-swap"

echo "sync-models: skeleton complete (wire the TODOs in PR 1)"
