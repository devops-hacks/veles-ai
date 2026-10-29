# Security baseline and hardening plan

Mirror of PDF Chapter 15 (v1.6): threat model, findings dossier S1-S13,
and the two-phase remediation that keeps delivery timescales unchanged.

Phase codes: **P0** = contained by design, verify during PR 0-2;
**P1** = hours of configuration, ships with v1; **P2** = hardening
backlog, scheduled after v1 stabilizes - never a delivery blocker.

## Phase 1 - day-one baseline (under half a day, folded into PR 0-2)

- [ ] (PR0) Passkeys/2FA on GitHub + Tailscale admin accounts; main-branch
      protection on. [P1, S9]
- [ ] (PR1) `sudo fdesetup status` reports FileVault is On. [P1, S2]
- [ ] (PR1) `chmod 600 ~/Library/"Application Support"/sops/age/keys.txt`. [P1, S2]
- [ ] (PR1) sshd_config: `PasswordAuthentication no`,
      `KbdInteractiveAuthentication no`. [P0, S13]
- [ ] (PR1) APFS-encrypt `/Volumes/ai-state` + every backup target. [P1, S10]
- [ ] (PR2) gateway.yml: `ENABLE_SIGNUP=false`; create admin first, members
      are users not admins. [P1, S8]
- [ ] (PR2) code-exec: `network_mode: none`, mem_limit/cpus caps, no
      docker.sock mount, ephemeral `--rm` lifecycle. [P0, S5, S12]
- [ ] (PR2) models.toml: explicit `sha256` per GGUF; sync-models.sh halts
      and notifies on mismatch. [P1, S7]
- [ ] (PR2) memory: namespaces.yaml with audit rule (Ch. 14 file). [P0, S1]
- [ ] (PR2) Family devices: Tailscale key expiry 90d; `tag:family` reaches
      443 only (Listing A-5). [P1, S4]

## Secrets workflow

- The age identity lives at `~/Library/Application Support/sops/age/keys.txt`
  (0600, dir 0700), backed up offline. Loss of the key = loss of every secret
  at once; the offline backup is the only recovery path.
- `sops secrets/<file>.yaml` is the only edit path: decrypts to `$EDITOR`,
  re-encrypts on save. Creation rules in `.sops.yaml` bind `secrets/*.yaml`
  to the household age recipient.
- No `.env` files, ever: secrets live sops-encrypted under `secrets/`;
  non-secret defaults live inline in compose/nix.
- Operator/agent boundary: the agent handles public-key wiring and ciphertext
  (`.sops.yaml`, `sops --encrypt --in-place`); the operator alone touches the
  private key and plaintext values. The agent never runs `sops -d`.

## Phase 2 - hardening backlog (starts after v1 stabilizes)

1. Stolen-device posture: Tailscale device posture checks; 90-day rotation
   on a calendar; revoke-first lost-device runbook; monthly device audit. [P2, S4]
2. Monitoring and alerting: sync failures, cert renewal failures, quota
   breaches, 401 storms, memory-service 5xx. [P2, S6]
3. Injection red-team corpus: hostile-document folder replayed against the
   RAG pipeline and family/ agent writes; gates every new tool (extends A3). [P2, S3]
4. Backup verification: timed restore of /Volumes/ai-state; recover the
   offline age key backup once under controlled conditions. [P2, S10]
5. Quarterly access review: tailnet devices, WebUI accounts, A1 keys, sops
   recipients, egress-ledger rows vs actual traffic. [P2, S9, S11]
6. CVE-driven patch override: critical CVE in an exposed surface (WebUI,
   llama.cpp, Tailscale client, OrbStack) = out-of-band PR within 48h. [P2, S8]

## Residual risk, accepted

Running unlocked Mac yields to a local attacker (FileVault protects at
rest only - screen lock is part of the posture); Tailscale control plane
is trusted (metadata-only); zero-days possible (deny-by-default scope +
CVE override bound the reach); model behavior not fully constrainable
(audit trail + guardian review are the backstop). Re-visited quarterly.
