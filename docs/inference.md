# Inference core runbook (roadmap PR 3)

What this ships: `llama-swap` as a system LaunchDaemon on 127.0.0.1:4002
with the three A1 keys sops-managed, plus the isolated 1.5B autocomplete
llama-server on 127.0.0.1:4003 (outside the swap matrix). sync-models is
roadmap PR 4 - until it lands, the autocomplete daemon stays down
(clean exit, no crash loop) and the swap matrix has no models to load.

## Findings and rulings (implementation record - read first)

1. **sops-install-secrets builds from source on darwin** and fetches Go
   modules from proxy.golang.org. This network blocks that host (DNS
   timeout), so `nix run nix-darwin -- build` fails here until the
   network allows it or the modules are vendored. Ledger row:
   `go-module-proxy`. No darwin substitute exists in nixpkgs yet.
   Switch is gated on the S9 proxy proof (architect).

2. **Launchd plist recursion - ROOT CAUSE CORRECTED.** First reported
   as `UserName` <-> users-module recursion; the S15 probe + bisect
   disproved that. Trigger: **passing a derivation as
   `serviceConfig.Program`** recurses infinitely in plist rendering at
   the pinned revs (nix-darwin bb0b90d / nixpkgs e62746b). Bisect:

   | shape | result |
  ---|---|
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

## Tier-0 boundary (standing, from the identity ruling)

The Mac is the identity host. Tier-0 acts are operator-only: age key
creation/backup, every `sops` decryption or edit, `darwin-rebuild`
switch, service smoke tests. The agent handles public-key wiring,
ciphertext, and code - and never decrypts (the Task-59 override is
RETIRED: any task that appears to require decryption is a STOP).

## Operator flow (after merge, on the Mac)

```bash
# 1. build (needs the go-module-proxy network path; see blockers above)
cd nix && nix run nix-darwin -- build --flake .#mac-ai   # dry gate - no switch
# 2. switch (operator-only, per house rules)
nix run nix-darwin -- switch --flake .#mac-ai
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
nix run nix-darwin -- switch --flake nix#mac-ai   # re-materializes secrets
sudo launchctl kickstart -k system/org.nixos.llama-swap
```

## The /run note

sops-nix materializes secrets under `/run/secrets/<name>` on darwin
(verified: `config.sops.secrets.<name>.path` evaluates to
`/run/secrets/llama_swap/<key>`). If a future sops-nix changes that
location, the fallback is a synthetic.conf entry providing the mount -
an architect decision, recorded here as the escape hatch only.
