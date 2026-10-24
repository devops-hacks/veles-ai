# veles-ai

Project code name: **Veles AI**. Declarative, local-first AI server for a
MacBook Pro M5 Max (128GB) household.
Companion repository to `Zero-Limit-Local-AI-Server-Architecture.pdf` (v1.6.1).
Start here: `docs/vscode-start-guide.md`, then `docs/pr-tdd-playbook.md`.

Every file in this kit is a **runnable skeleton with TODO markers** — real values
replace `<placeholders>`; nothing here is a stub to delete.

## Bootstrap order

0. **Full step-by-step walkthrough: `docs/vscode-start-guide.md`** (fresh Mac
   to first merged PR, ~45 min). Decisions it locks in: repo root is
   `~/veles-ai` (under `$HOME`, outside iCloud-synced folders, no spaces;
   heavy state stays on `/Volumes/ai-models` + `/Volumes/ai-state`), and
   **remote-first** — private GitHub repo + branch protection exist before
   the first commit.
1. Create the **private** GitHub repo (`veles-ai`), protect `main`, clone
   to `~/veles-ai`, copy this kit in, single bootstrap commit (PR 0).
   PR/CI gates (`.github/`, `.pre-commit-config.yaml`) ship in the kit —
   process + TDD rules: `docs/pr-tdd-playbook.md`.
2. Fill `models/models.toml` with your pinned GGUF set; run `scripts/sync-models.sh`
   against a mounted `/Volumes/ai-models`.
3. Wire `nix/flake.nix` (llama-swap launchd service + sync timer), then
   `darwin-rebuild switch --flake .#mac-ai` (PR 1).
4. Implement amendments A1 (per-consumer gateway keys) and A2 (memory
   namespaces) before anything depends on them (PR 2); seed
   `services/memory/namespaces.example.yaml` (Chapter 14: private |
   family, read-shared/write-private) as the A2 configuration.
5. Point clients at the gateway (see `clients/vscode/`).

## GitHub repo setup

```bash
# on the Mac (server) — full walkthrough: docs/vscode-start-guide.md §3-4
brew install gh git pre-commit
gh auth login
# 1. browser: create EMPTY private repo `veles-ai` + protect main
#    (require PR, status checks: lint + test)
# 2. clone and copy the kit in — the only direct push to main is bootstrap:
git clone git@github.com:YOU/veles-ai.git ~/veles-ai
cd ~/veles-ai && chmod 700 .
cp -R ~/Downloads/veles-ai-kit/. .
pre-commit install && pre-commit run --all-files
git add -A && git commit -m "chore: bootstrap from starter kit" && git push origin main
```

## VS Code setup (primary: on the Mac itself; secondary: Win11 laptop)

0. **Primary loop is VS Code running on the Mac** — localhost endpoints, no
   Remote-SSH hop; see `docs/vscode-start-guide.md` §2. Win11 below is the
   secondary editing path.
1. Enable Remote Login (SSH) on the Mac: System Settings > General > Sharing.
2. In VS Code install: **Remote - SSH**, **Cline**, **Continue**, **GitLens**.
3. Remote-SSH into `ssh <you>@mac.<tailnet>.ts.net` for server-side files
   (nix/, services/, models/) — the repo lives on the Mac; the laptop edits it.
4. Cline: OpenAI-Compatible provider, baseURL `http://mac.<tailnet>.ts.net:4002/v1`,
   API key = its own A1 consumer key, Plan/Act split enabled.
5. Continue: copy `clients/vscode/continue.config.yaml` to
   `%USERPROFILE%\.continue\config.yaml` and fill the tailnet name + key.
6. Claude Code stays cloud-authenticated (Plan-on-cloud / Act-local, Ch. 7).

## Working agreement

- One PR per change; every roadmap feature passes the gate in `docs/roadmap.md`.
- TDD from day one: red test → green → refactor; PR checklist + AI review
  per `docs/pr-tdd-playbook.md`; CI enforces lint + tests + coverage ≥ 85%
  (floor raised to 90% after the first month).
- `darwin-rebuild build` (dry) before `switch`; rollback on failed health gates.
- Secrets only via sops (`.sops.yaml`); the age key never enters git.
- Security baseline (`docs/security.md`, Phase 1) is part of PR 0-2; the
  hardening backlog starts after v1. Egress only via `docs/egress-ledger.yaml`
  - a feature adds a ledger row before it adds traffic.
