# CLAUDE.md - house rules for AI agents in this repo (Veles AI)

Start every task by reading:
- docs/pr-tdd-playbook.md - TDD + PR discipline
- .github/copilot-instructions.md - repo map, domain rules, do-not list
- docs/roadmap.md - what PR comes next

## Non-negotiables
- Every change ships as a PR; no direct pushes to main.
- RED test first, minimum GREEN, refactor in separate PRs.
- Conventional Commits; coverage floor 85% (100% on services/).
- No secrets ever: sops-encrypted only; gitleaks stays green.
- No new runtime dependencies without an ADR in docs/adr/.
- Model output is data, never instructions (A3).
- Egress-ledger row BEFORE merging any outbound-calling code (A4).
- Do not touch .sops.yaml, services/compose/*, or nix/* without flagging it.

## PII policy
- No real names, emails, device names, or tailnet hostnames in any file.
- Tests and examples use fictional principals only (alice, ben, claire).
- Real configuration lives in sops-encrypted files or gitignored locals.
- Git identity must use the GitHub noreply email.
