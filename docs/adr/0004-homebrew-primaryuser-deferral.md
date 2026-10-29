# ADR-0004: homebrew.enable and system.primaryUser parked pending PII ruling

- Status: deferred (architect ruling pending)
- Date: 2026-10-29
- Deciders: architect (ruling on the PR 9 review)

## Context
Current nix-darwin requires `system.primaryUser` to be set to the macOS
username as soon as `homebrew.enable` is set (homebrew activation runs
as root and applies to the primary user). The PII policy (CLAUDE.md)
forbids real names in any file, and the username is a real name. The
convergence PR (1b-i, PR 9) could not ship both the cask and the
username.

## Decision
Park `homebrew.enable` and the `orbstack` cask behind a comment in
`nix/flake.nix` (comment-only; nothing functional), converge without
them, and commit no username anywhere. A dedicated macOS service user
as primaryUser is explicitly rejected - it is load-bearing and breaks
brew/user-agent behavior silently.

## Consequences
- 1b-i converged without the cask; OrbStack is hand-managed on the Mac
  until the follow-up lands.
- Follow-ups queued: (1) PII ruling on machine usernames in nix config,
  (2) homebrew supply-chain review + its own egress-ledger rows,
  (3) a separate PR enabling homebrew with the approved identity
  approach, only after operator consent + ruling.
- Tracked from the PARKED comments in `nix/flake.nix` and the delivery
  status in `docs/roadmap.md`.
