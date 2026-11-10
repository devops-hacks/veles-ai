# ADR-0002: Declarative configuration via nix-darwin + sops + GitOps

- Status: accepted
- Date: 2026-10-18
- Amended: 2026-11-11 - the `scripts/gitops-apply.sh` named below is a
  planned seam, not shipped; today's apply path is
  `scripts/bootstrap.sh` plus the operator flow in docs/inference.md
  (dry `build`, root-only `switch`, launchd smoke tests).

## Context
A one-operator household still needs reproducibility, secrets, and a rollback
path; imperative macOS setup rots silently.

## Decision
nix-darwin flake declares services (llama-swap via launchd, sync timers);
secrets are age-encrypted in-repo via sops; changes travel as PRs and are
applied by `scripts/gitops-apply.sh` with health gates and rollback.

## Consequences
Hardware swaps become declarative applies (Ch. 12); contributors must learn
minimal Nix; every service gains a rebuild-rollback story for free.
