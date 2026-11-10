# Bootstrap - reproducible bring-up (1b-ii)

`scripts/bootstrap.sh` is the reproducible path from a bare arm64 macOS
to the converged darwin config. It is disaster-recovery tooling: the
same steps, verified, every time. Design rule: fail closed - every step
verifies, any failure stops the run.

## Usage

```bash
scripts/bootstrap.sh --check   # verify-only: no mutation, no downloads
scripts/bootstrap.sh           # apply: install (if needed), converge, verify
```

Idempotent and safe to re-run; every step detects existing state first.

## What it does

1. **Preflight** - darwin/arm64, Xcode CLT, git.
2. **Nix** - present: verify. Absent: download the **pinned**
   Determinate installer release, verify its sha256 against the hash in
   the script, run it.
3. **Repo** - locate the checkout (or clone from the canonical URL);
   HEAD must match `origin/main`; apply mode also requires a clean tree.
4. **Converge** - the proven 1b-i command, root-only on nix-darwin
   26.11: `sudo "$(command -v nix)" run nix-darwin -- switch --flake
   <repo>/nix#mac-ai`. Standing prerequisites (findings 4-8 in
   docs/inference.md): the flake module must carry
   `nix.enable = false;` (ADR-0005) - PENDING PUSH, not yet on main;
   until that PR lands, confirm the local checkout carries it or the
   switch aborts with "Determinate detected" - and
   `/etc/synthetic.conf` must carry the `/run` firmlink (verified
   below). KNOWN GAP (2026-11-11): the script's converge step still
   runs the switch WITHOUT sudo - until a reviewed code PR lands it,
   run the switch by hand with the command above. The lock is
   sacred: the script NEVER runs `nix flake update`.
5. **Identity** - operator-handled, never scripted: if `sops.secrets`
   are defined, verify the age key exists and print placement
   instructions; check Tailscale presence and print join instructions.
   The script never creates, moves, decrypts keys, or authenticates.
   KNOWN GAP (2026-11-11): the script's age-key check still greps
   `nix/flake.nix` only and misses `nix/inference.nix`, where PR 3
   moved the `sops.secrets` - verify the age key by hand until the
   same code PR as the sudo converge fixes the grep path.

## Trust anchor (installer)

- Pinned twice: release **version** (`v3.24.1`) and **content sha256**
  (from the release asset digest), both constants in the script.
- Fetched over HTTPS from github.com release assets. No
  "pipe-to-shell" one-liner - unverifiable by construction.
- Upstream publishes no per-version checksums file for release assets;
  the in-repo hash is the verification. Changing either constant is a
  reviewed PR.

## /run firmlink prerequisite (verify; repair is boot-time)

nix-darwin 26.11 activation requires `/run` as the synthetic firmlink
`run -> private/var/run` (findings 7-8, docs/inference.md). The
OPERATOR verifies this on every bring-up - the script does not check
it yet (same gap class as the sudo converge above); treat an absent
firmlink as a failed bring-up. The repair is a boot-time operator act,
never a scripted mutation:

```bash
sudo cat -et /etc/synthetic.conf   # expect: run^Iprivate/var/run$
ls /run                            # non-empty (contents of /var/run)
```

Absent or bare (`run` with no target)? Fix once, then reboot - boot
rebuilds `/run` from synthetic.conf; there is no runtime repair:

```bash
printf 'nix\nrun\tprivate/var/run\n' | sudo tee /etc/synthetic.conf
sudo reboot
```

That printf rewrites the whole file - the `nix` store entry is
preserved in it; re-add any other entries synthetic.conf carried.

## Standing bring-up gates

Enforced at the phases that own them (see roadmap "Bring-up gates"):

- **SR-01** gateway auth lands WITH llama-swap;
- **SR-02** WebUI first-admin + closed signups;
- **SR-03** loopback-only binds except the TLS terminator.

## WARNING - scrub transcripts before public paste

Activation and switch output prints absolute paths under your home
directory. If you paste a run transcript into an issue, PR, or chat,
scrub those lines first.
