# PR & TDD Playbook

How every change lands in this repo: gated, reviewed, tested-first.
Ties into `docs/roadmap.md` (feature gate G1–G6), `docs/security.md`
(Phase 1 checklist) and `docs/egress-ledger.yaml` (A4).

## 1. Non-negotiables

1. `main` is protected and always deployable. PR-only, squash-merge,
   delete the branch afterwards.
2. No change is too small for a PR — the habit is the product. CI runs
   regardless of size, so the gate stays warm.
3. TDD: no production code without a failing test written first
   (red → green → refactor).
4. Every PR is reviewed twice: by you (self-review the diff) and by your
   AI reviewer (Cline) against the checklist in the PR template.
5. New outbound traffic = a new row in `docs/egress-ledger.yaml` **before**
   the merge (A4 — no undeclared channels, Ch. 15).

## 2. Conventions

- Branches: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.
- Commits: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`,
  `chore:`) — the subject line becomes the squash-merge title.
- PRs: one logical change; link the roadmap row, ADR or finding ID
  (S1–S13) it implements when applicable.
- ADR: any decision that flips a trade-off gets a `docs/adr/00xx-*.md`.

## 3. The review loop (solo, with AI)

1. **Self-review first.** Read the full diff as a reviewer before pushing.
   Most nits die right here, and the AI pass gets a cleaner diff.
2. **AI review.** In VS Code (Cline, local models via the gateway),
   paste the PR description + diff and prompt:

   > Review this diff against `.github/pull_request_template.md`.
   > Flag: correctness, security (secrets, injection, permissions, new
   > ports/endpoints/mounts), test gaps, and design drift (namespaces /
   > amendments A1–A6 / egress ledger). Ignore style — pre-commit owns it.

   Optionally enable GitHub's automatic Copilot PR review as a second,
   independent pass on github.com. Copilot surfaces (chat, coding agent,
   PR review) read `.github/copilot-instructions.md` for repo conventions —
   keep that file in sync whenever this playbook changes.
3. **Address or rebut every finding** in commits on the same branch; CI
   re-runs automatically.
4. **Merge rules:** CI green + checklist complete + no unresolved findings
   → squash merge. You are the approver; the checklist plus the AI pass are
   the second pair of eyes.

## 4. TDD rules

- **Red first, for the right reason** — the failure message must match the
  new behavior, not a typo or an import error you meant to fix anyway.
- **Green is minimum code.** No speculative branches; the coverage gate
  keeps you honest (85% now, raise to 90% after the first month — bump
  `--cov-fail-under` in `.github/workflows/ci.yml` and in this file).
- **Refactor with the tests green.** Behavior PRs and refactor PRs do not
  mix — two small PRs beat one big one.
- Test layers:
  - *unit* — pure logic, no I/O (`tests/`, pytest); the default layer;
  - *contract* — the memory adapter's 4-op contract (remember / recall /
    search / commit-session, Ch. 5) against a fake OpenViking backend;
  - *shell specs* — `bats tests/` for scripts like `sync-models.sh`;
  - *integration* — `docker compose up` smoke tests run **on the Mac,
    never in CI** (GitHub runners have no Metal/GPU).
- Exempt from unit tests: declarative config (nix, compose, YAML) —
  verified by the lint/validation gates instead of unit tests.

## 5. CI today, CI after PR 1

| Job | Runs | Gate |
|---|---|---|
| `lint` | `pre-commit run --all-files` | ruff, format, shellcheck, yamllint, gitleaks, private-key detect |
| `test` | `pytest --cov=services --cov-fail-under=85` | a red PR is a red CI |
| `test` (conditional) | `bats tests/` | activates when the first `.bats` spec lands |

Deliberately **not** in CI yet:

- `docker compose -f services/compose/*.yml config -q` — add in PR 1 once
  images carry real pinned digests (the `<pinned-digest>` placeholders
  would fail validation today);
- `nix flake check` — add after PR 1 (eval-only on ubuntu runners; the
  darwin activation stays a local `darwin-rebuild build` dry-gate per
  README).

## 6. Coverage policy

- The floor is `pytest --cov=services --cov-report=term-missing
  --cov-fail-under=85`, enforced in CI from the first PR.
- HTML view: `pytest --cov=services --cov-report=html` →
  `open htmlcov/index.html`.
- `# pragma: no cover` only for glue that needs a live Mac (launchctl,
  Metal paths); every waiver carries a TODO comment linking a finding ID
  or ADR.
