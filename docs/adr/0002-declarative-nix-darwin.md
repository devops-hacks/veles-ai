# ADR-0002: Declarative configuration via nix-darwin + sops + GitOps

- Status: accepted
- Date: 2026-10-18
- Amended: 2026-11-11 - the `scripts/gitops-apply.sh` named below is a
  planned seam, not shipped; today's apply path is
  `scripts/bootstrap.sh` plus the operator flow in docs/inference.md
  (dry `build`, root-only `switch`, launchd smoke tests). Until
  `gitops-apply.sh` ships, that path still converges and stays
  idempotent: `scripts/bootstrap.sh` is safe to re-run (existing state
  detected, never re-applied), the dry `build` gate precedes every
  root-only `switch`, `nix/flake.lock` moves only through a reviewed
  PR, and the guard tests (pin guards, egress ledger, lock allowlist)
  block drift. One-time boot-time repairs (the `/run` firmlink fix and
  reboot) sit outside the loop; the standing check for them is
  idempotent.

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
