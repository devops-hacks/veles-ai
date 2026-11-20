# Inference core runbook (roadmap PR 3)

What this ships: `llama-swap` as a system LaunchDaemon on 127.0.0.1:4002
with the three A1 keys sops-managed, plus the isolated 1.5B autocomplete
llama-server on 127.0.0.1:4003 (outside the swap matrix). sync-models is
roadmap PR 4 - until it lands, the autocomplete daemon stays down
(clean exit; "no crash loop" holds only with PR 19's
`KeepAlive.SuccessfulExit = false`, finding 6) and the swap matrix has
no models to load.

## Findings and rulings (implementation record - read first)

1. **sops-install-secrets builds from source on darwin** and fetches Go
   modules from proxy.golang.org. This network blocks that host (DNS
   timeout), so `nix run nix-darwin -- build` fails here until the
   network allows it or the modules are vendored. Ledger row:
   `go-module-proxy`. No darwin substitute exists in nixpkgs yet.
   Switch is gated on the S9 proxy proof (architect).

   **RESOLVED 2026-11-11:** the full darwin-system closure - sops
   included - built on this network during the dry-gate rebuild; the
   blocker did not reproduce. No vendoring. The ledger row stays: a
   fresh machine may still fetch go-modules (content-hashed by nix).
   The S9 proxy gate is lifted by this resolution; the remaining
   switch conditions are PR 19 and PR 20 (roadmap 2026-11-11 update).

2. **Launchd plist recursion - ROOT CAUSE CORRECTED.** First reported
   as `UserName` <-> users-module recursion; the S15 probe + bisect
   disproved that. Trigger: **passing a derivation as
   `serviceConfig.Program`** recurses infinitely in plist rendering at
   the pinned revs (nix-darwin bb0b90d / nixpkgs e62746b). Bisect:

   | shape | result |
   |---|---|
   | derivation Program + UserName + declared user | overflow |
   | derivation Program + UserName, inert strings, declared user | overflow |
   | derivation Program + UserName, NO user declarations | overflow |
   | **string Program + UserName + everything else** | **builds** |
   | string Program + UserName + undeclared user (sops-free probe) | builds |

   Fix: `command = "<wrapper path>"` (string-coerced) instead of
   `serviceConfig.Program`; guards + strict-eval CI gate keep it shut.
   No matching upstream issue exists (searched 2026-11); upstreaming is
   an architect option. `UserName = "_veles"` is safe and kept.

3. **Pattern (b) - no nix user declarations (architect-approved).** The
   module declares NO `users.*` entries; the hidden `_veles` service
   account is operator-created once, outside nix:

   ```bash
   # tier-0 (operator, once): create the hidden service account
   # GROUP FIRST, then the user that joins it:
   sudo dscl . -create /Groups/_veles
   sudo dscl . -create /Groups/_veles PrimaryGroupID 490
   sudo dscl . -create /Users/_veles
   sudo dscl . -create /Users/_veles UniqueID 490
   sudo dscl . -create /Users/_veles PrimaryGroupID 490
   sudo dscl . -create /Users/_veles NFSHomeDirectory /var/empty
   sudo dscl . -create /Users/_veles UserShell /usr/bin/false
   sudo dscl . -create /Users/_veles IsHidden 1
   sudo dscl . -create /Users/_veles RealName "veles-ai inference service account"
   # no password / AuthenticationAuthority key at all
   # pre-switch verify (expect 7 key-value rows):
   sudo dscl . -read /Users/_veles
   ```
   Executed 2026-11-03, verified 7/7 - do not re-run on an existing account.

   (Account existence is asserted at smoke-test time; the activation
   chown runs as root and needs only the names.)

4. **llama-swap release assets drop the `v` (2026-11-11, dry-gate
   rebuild).** Tags read `vNNN`; asset filenames read
   `llama-swap_NNN_darwin_arm64.tar.gz` - verified against the release
   API at v120, v268, v270, and v271. The PR 18 URL templated the tag into
   the filename, so `fetchurl` 404'd (`curl: (22)`, three retries).
   The SRI hash on main was already correct - it was taken from the
   real asset's digest. Fix (carried by PR 20): pin the bare
   `LLAMA_SWAP_VERSION = "268"`, keep the tag `v${LLAMA_SWAP_VERSION}`
   in the URL path segment, and build the filename from the version
   WITHOUT the leading `v`; hash and pin discipline unchanged.

5. **Flat release tarball (same rebuild).** The darwin-arm64 tarball
   unpacks its files at the top level - no wrapper directory - so the
   default `unpackPhase` aborts ("unpacker appears to have produced no
   directories"). Fix (carried by PR 20): `sourceRoot = ".";` on the
   derivation; the binary then sits at `./llama-swap` for the
   installPhase.

6. **KeepAlive semantics (PR 19, merged 2026-11-11).**
   `KeepAlive = true` restarts a job
   on EVERY exit, so the autocomplete daemon's intentional clean
   exit-0 (model absent until PR 4) became an exit-loop. Ruling
   (restores the launcher's stated no-crash-loop contract):
   `KeepAlive.SuccessfulExit = false` - restart on
   crash/abnormal exit only; a deliberate exit-0 stays down until
   RunAtLoad or a manual `launchctl kickstart`. The "stays down, no
   crash loop" contract above is true only with this setting.

7. **Activation is root-only, and Determinate is detected hard
   (nix-darwin 26.11).** A plain `nix run nix-darwin -- switch`
   aborts with "system activation must now be run as root"; with
   Determinate installed (the bootstrap.sh path) activation also
   aborts - "Determinate detected" - unless the flake module carries
   `nix.enable = false;`. The check (upstream
   `modules/system/checks.nix`) tests for
   `/usr/local/bin/determinate-nixd`; no flag or env var bypasses it.
   Ruling: `nix.enable = false;` in the flake (ADR-0005 - Determinate
   keeps owning Nix; nix-darwin keeps everything else), and the
   switch runs as
   `sudo "$(command -v nix)" run nix-darwin -- switch ...` - the
   command-v indirection survives sudo's PATH reset; plain
   `sudo nix` often does not.

8. **`/run` firmlink is a boot-time prerequisite (same rebuild).**
   nix-darwin 26.11 materializes the system profile under `/run`, so
   `/etc/synthetic.conf` must carry the firmlink
   `run -> private/var/run` (TAB-separated). Two traps hit on the
   host: a bare `run` line creates an empty DIRECTORY at boot, not a
   firmlink, and that stale directory then blocks repair - `apfs.util
   -t` cannot create the firmlink over it, and the root filesystem is
   read-only while booted (`rmdir /run` -> "Read-only file system").
   Fix: correct the line once, then REBOOT - boot rebuilds `/run`
   from synthetic.conf; there is no reliable runtime repair. Verify:
   `sudo cat -et /etc/synthetic.conf` shows `run^Iprivate/var/run$`;
   `ls /run` lists the contents of `/var/run` (non-empty).

## Tier-0 boundary (standing, from the identity ruling)

The Mac is the identity host. Tier-0 acts are operator-only: age key
creation/backup, every `sops` decryption or edit, the root-only
switch (finding 7), service smoke tests. The agent handles public-key wiring,
ciphertext, and code - and never decrypts (the Task-59 override is
RETIRED: any task that appears to require decryption is a STOP).

## Operator flow (after merge, on the Mac)

```bash
# 0. standing prerequisites (findings 7-8): the flake must carry
#    nix.enable = false (carried by PR 20); /run firmlink
#    present (boot-time, finding 8)
# 1. build (dry gate - no switch; go-module-proxy blocker RESOLVED 2026-11-11)
nix run nix-darwin -- build --flake ./nix#mac-ai
# 2. switch (operator-only; root-only activation on nix-darwin 26.11 - finding 7)
sudo "$(command -v nix)" run nix-darwin -- switch --flake ./nix#mac-ai
# 3. control
sudo launchctl kickstart -k system/org.nixos.llama-swap
sudo launchctl kickstart -k system/org.nixos.llama-autocomplete
sudo launchctl print    system/org.nixos.llama-swap     # status
sudo launchctl bootstrap system /run/current-system...   # rarely needed; switch bootstraps
# stop/start pairs: bootout + bootstrap
```

## Smoke-test contract (operator)

- `curl -s http://127.0.0.1:4002/health` -> OK, **unauthenticated**
  (upstream contract: /health is open; everything else requires a key).
- Unauthenticated model call -> **401**:
  `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:4002/v1/models`
- Authenticated call with the operator key (from the sops file, operator
  decrypts for the test) -> **200**.
- Autocomplete tier: before PR 4 syncs models, the daemon logs the
  "model absent - staying down" line and exits 0; after sync,
  `curl -s http://127.0.0.1:4003/health` -> OK.
- SR-01 evidence: keys live at the router (401 without, 200 with) and
  binds are loopback-only (see the source guards).
- WebUI route (verified 2026-11-20): `curl /ui/` -> **401** without
  key, **200** with the operator key - the A1 gate covers the router's
  UI, not just `/v1/*`.

## Serving proof (2026-11-20, scripted, PR 30 post-deploy)

The llama-swap WebUI path was proven end-to-end with scripted,
pre-declared gates (W1/W2/W2b/W2c) - the same endpoint and key the
browser session uses, driven non-interactively:

- Catalog: `/v1/models` lists exactly the swap-matrix model
  `qwen3-coder-30b-a3b` (the isolated 1.5B tier is outside the matrix
  by design); llama-swap pid 60176 throughout the PR 30 deploy.
- Completion: `/v1/chat/completions` returned the exact requested
  phrase (`VELES-WEBUI-PROOF-OK`, finish `stop`) through the swap
  matrix; artifact `/tmp/w2-completion.json`.
- Upstream spawn pinned: llama-server pid 95361, store binary
  `llama-cpp-0.7.0`, `-ngl 99 -fa on -ctk q8_0 -ctv q8_0 -c 131072
  -np 8 --cont-batching --cache-reuse 256`, upstream port 5800.
- WebUI: served at `http://127.0.0.1:4002/ui/` (`Location: ui/`
  redirect); **401 without key, 200 with the operator key** - the A1
  key gate covers the UI route, not just `/v1/*` (artifact
  `/tmp/w2c-ui.html`).
- Idle unload: `globalTTL: 1800` unloads after ~30 min idle
  (`status: unloaded` in the catalog, no llama-server process); a
  scripted request re-spawns on demand (1.4 s warm).
- Known wart (docs-only): the catalog advertises `context_length:
  16384` while the spawned cmd runs `-c 131072` - two sources of
  truth; reconcile in the PR 5 window.

## Logs and Metal verification

- Router logs: stdout via launchd (`/var/log/` redirection is a Phase 2
  item) or llama-swap's `/logs` endpoints once serving.
- Metal: once models land (PR 4), llama-server logs a
  `ggml_metal: found device` line on load. **If Metal is unavailable in
  the daemon context, STOP and escalate** - Plan B is a runtime-rendered
  LaunchAgent with @USER@ substitution (architect decision, not an
  improvisation).

## Key rotation

```bash
sops secrets/llama-swap.yaml     # edit values, save (re-encrypts)
git commit the ciphertext        # reviewed PR as usual
# on the Mac:
sudo "$(command -v nix)" run nix-darwin -- switch --flake ./nix#mac-ai   # re-materializes secrets
sudo launchctl kickstart -k system/org.nixos.llama-swap
```

## The /run note

sops-nix materializes secrets under `/run/secrets/<name>` on darwin
(verified: `config.sops.secrets.<name>.path` evaluates to
`/run/secrets/llama_swap/<key>`). If a future sops-nix changes that
location, the fallback is a synthetic.conf entry providing the mount -
an architect decision, recorded here as the escape hatch only.

**Standing prerequisite (finding 8, nix-darwin 26.11):** `/run` itself
must exist as the synthetic firmlink `run -> private/var/run` before
any switch. Idempotent check:

```bash
sudo cat -et /etc/synthetic.conf   # must contain: nix$ and run^Iprivate/var/run$
ls /run                            # non-empty (contents of /var/run)
```

Missing or bare (`run` with no target)? Fix once and REBOOT - the
firmlink only materializes at boot:

```bash
printf 'nix\nrun\tprivate/var/run\n' | sudo tee /etc/synthetic.conf
```

That printf rewrites the whole file - the `nix` store entry is
preserved in it; re-add any other entries synthetic.conf carried.

The escape-hatch paragraph above predates finding 8: the
synthetic.conf entry is now load-bearing, not hypothetical.

9. **Model-volume ownership: activation ran before the mount
   (2026-11-16, PR 4).** The activation chown to `_veles:_veles` was
   declared but never materialized; Gate G-1 shows the volume mounts
   with `Owners: enabled`, so the silent swallow (`|| true`) hid a real
   failure - at switch time the volume path predates the mount or the
   chown was refused. The activation script now fails LOUD (grep-able
   `MARKER-A2`) without bricking the switch; the volume-tolerant else
   branch (services stay up) is unchanged. Runbook: re-run the switch
   with the volume mounted; the chown materializes.

   **RESOLVED 2026-11-18 (PR 29, commits 46882ca + 5c17cdd).** Root
   cause: the chown lived in custom activation chunks
   (`llamaModelsVolume`, `velesLogDir`) that nix-darwin bb0b90d never
   wires - custom chunk names are dead code (the PR 27 ruling). The
   cure moved the work into the WIRED `postActivation.text`
   (types.lines) with a class-closure guard test. Deploy evidence:
   switch log carries `veles: model volume ownership verified
   (_veles:_veles)` exactly once, `MARKER-A2` absent, gguf at
   `_veles:_veles`, `/var/log/veles` provisioned and owned.
   Re-verified unchanged on the PR 30 switch (2026-11-20).

10. **Silent curl stall - `--retry` cannot see a stall (2026-11-18,
    cured by PR 30, deployed 2026-11-20).** First full model-sync run
    (17 GiB qwen3 + 1.8 GiB qwen2.5, ~19 h wall clock): four curl
    instances for the 30B tier, three loud `FAIL:` lines in .err - and
    one SILENT stall: the .part sat at 8.0 GiB with a frozen mtime for
    many minutes, no retry fired (`--retry` retries curl ERRORS; a
    stalled-but-open TCP connection produces none), recovery required a
    manual `launchctl kickstart -k`. Resume integrity held throughout
    (`-C -` preserved the 8.0 GiB across kills; the final files hashed
    to the manifest pins `fadc3e5f...` / `507de590...`; idempotent
    re-run printed `OK (cached, hash verified)` twice). Cure (PR 30,
    one transport line): `--speed-limit 1024 --speed-time 60` - under
    1 KB/s for 60 s aborts with exit 28, which `--retry` treats as
    transient: self-abort, auto-resume via `-C -`, die loud only after
    three in-process retries. A healthy multi-MB/s transfer cannot trip
    the guard. Guard test pins the curl line byte-for-byte; RED-first
    evidence in the PR body. Deploy chain on record: system
    `a1ppylw02qks6bs2hzmglh8f5cdk7r47-darwin-system-26.11.bb0b90d`,
    launcher `8j5wwh2h...`, inner `qxspxhi3...`; post-switch
    idempotence kick: cached OK twice, `no orphans`, `done`, zero curl.

