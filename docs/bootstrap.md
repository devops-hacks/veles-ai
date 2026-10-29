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
4. **Converge** - the proven 1b-i command:
   `nix run nix-darwin -- switch --flake <repo>/nix#mac-ai`.
   The lock is sacred: the script NEVER runs `nix flake update`.
5. **Identity** - operator-handled, never scripted: if `sops.secrets`
   are defined, verify the age key exists and print placement
   instructions; check Tailscale presence and print join instructions.
   The script never creates, moves, decrypts keys, or authenticates.

## Trust anchor (installer)

- Pinned twice: release **version** (`v3.24.1`) and **content sha256**
  (from the release asset digest), both constants in the script.
- Fetched over HTTPS from github.com release assets. No
  "pipe-to-shell" one-liner - unverifiable by construction.
- Upstream publishes no per-version checksums file for release assets;
  the in-repo hash is the verification. Changing either constant is a
  reviewed PR.

## Standing bring-up gates

Enforced at the phases that own them (see roadmap "Bring-up gates"):

- **SR-01** gateway auth lands WITH llama-swap;
- **SR-02** WebUI first-admin + closed signups;
- **SR-03** loopback-only binds except the TLS terminator.

## WARNING - scrub transcripts before public paste

Activation and switch output prints absolute paths under your home
directory. If you paste a run transcript into an issue, PR, or chat,
scrub those lines first.
