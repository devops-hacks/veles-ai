## What & why
<!-- 1-2 sentences. Link the driver: roadmap row, ADR, finding S1-S13, or issue. -->

## TDD evidence
- [ ] Failing test written first (`pytest -q` showed RED before implementation)
- [ ] GREEN locally: `pytest -q`
- [ ] Coverage gate holds: `pytest --cov=services --cov-fail-under=85`

## Gates
- [ ] `pre-commit run --all-files` clean
- [ ] No secrets/keys in the diff (gitleaks green) — sops ciphertext only
- [ ] New outbound traffic? Row added to `docs/egress-ledger.yaml` BEFORE merge (A4)
- [ ] compose/nix touched? `darwin-rebuild build` (dry) ran on the Mac
- [ ] Docs updated (README / docs/) when setup or behavior changed

## Security & privacy (Ch. 15 lens)
- [ ] No PII in diff - fictional fixtures only; no real names,
      emails, device names, or tailnet hostnames
- [ ] No new ports, endpoints, or mounts without a note here justifying them
- [ ] Memory touched? Namespace rules respected (A2: owner-only `users/`,
      household `family/`, guardian-only delete) + audit trail intact
- [ ] Untrusted content stays DATA, never instructions (A3 / gate G4)

## Review
- AI reviewer findings addressed: <!-- list, or "none" -->
- Checklist self-review done before requesting merge
