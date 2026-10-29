# Flake update procedure

How `nix/flake.lock` moves. The lock is the system's version pin
(Ch. 8); updating it is a deliberate, reviewed act - never a side effect.

## Cadence

- **Monthly:** a scheduled refresh of all inputs, in the monthly upgrade
  window (operating calendar, PDF Ch. 10).
- **Immediately:** on a security advisory touching a pinned input
  (nixpkgs, nix-darwin, sops-nix). Do not batch it into the monthly
  window.

## Procedure

1. Worker: `cd nix && nix flake update`.
2. Worker: open a lock-diff PR. The body MUST summarize each input as
   `old rev -> new rev` (the guard tests in `tests/nix/` keep the lock
   structurally honest; the summary keeps it reviewable).
3. CI: the `nix` eval job must pass on the PR (build proof stays local
   to the Mac - ubuntu cannot build darwin closures).
4. Operator: merge.
5. Operator: run the switch on the Mac. **The switch is
   operator-only - never the worker.**

## Rollback

1. Revert the lock commit (a normal revert PR, or `git revert` on the
   branch for urgent cases).
2. Re-run the switch with the restored lock. Generations remain
   available as a second belt: `darwin-rebuild --rollback`.

## Constraints

- **Owner allowlist:** adding an input whose owner/repo is not in
  `GITHUB_OWNER_ALLOWLIST` (`tests/nix/test_flake_lock.py`) requires an
  explicit architect note in the PR - the allowlist edit and the lock
  change travel together.
- **Floating refs:** banned forever, repo-wide (`latest` ban, enforced
  by `tests/ci/test_action_pins.py` for actions).
- **Egress:** ledger rows `flake-inputs` / `nix-cache`
  (`docs/egress-ledger.yaml`) already cover the fetch traffic. Add a row
  only if an update introduces a host not already enumerated there.
