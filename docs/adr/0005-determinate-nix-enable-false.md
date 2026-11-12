# ADR-0005: Determinate stays; nix-darwin manages everything except Nix

- Status: accepted
- Date: 2026-11-11
- Deciders: operator (ruling on the 2026-11-11 dry-gate rebuild)

## Context

`scripts/bootstrap.sh` installs Nix via the pinned Determinate
installer (version + content-hash pinned), so Determinate's daemon
owns the Nix installation. nix-darwin 26.11 also manages Nix by
default (`nix.enable = true`) - same launchd daemon, same
`/etc/nix/nix.conf`. Activation aborts hard: "Determinate detected,
aborting activation". The check (upstream
`modules/system/checks.nix`) tests for
`/usr/local/bin/determinate-nixd` and has no bypass flag or env var.
Activation is additionally root-only on this nix-darwin generation
("system activation must now be run as root").

## Decision

Set `nix.enable = false;` in the darwin module (`nix/flake.nix`) and
keep Determinate as the sole owner of the Nix installation. The switch
runs root-only:

```bash
sudo "$(command -v nix)" run nix-darwin -- switch --flake ./nix#mac-ai
```

The `command -v` indirection survives sudo's PATH reset; plain
`sudo nix` often does not. Run from the repo root - the flake lives
at `nix/flake.nix`.

## Consequences

- nix-darwin keeps managing launchd services, `/etc`, activation -
  everything except Nix itself.
- The `nix.*` option family is unavailable in the config (settings,
  gc, package, linux-builder). Nix settings stay with Determinate;
  changing them is a host-level operator act, not a repo PR. The
  option family is unused in this flake today.
- Alternative rejected: migrating off Determinate to the standard
  installer to regain `nix.*` - churn (uninstall, reboot, reinstall)
  with no offsetting benefit.
- Once PR 20 (`nix.enable = false;`, open as of 2026-11-11) and the
  bootstrap.sh converge PR (sudo + `/run` check - the KNOWN GAP in
  docs/bootstrap.md) land, bootstrap.sh and the flake are mutually
  consistent and a fresh bootstrap converges in one pass. Until then
  a fresh bootstrap needs the operator's hand for the switch.
- Related standing prerequisite, same rebuild: the `/run` firmlink
  (findings 7-8, docs/inference.md).
