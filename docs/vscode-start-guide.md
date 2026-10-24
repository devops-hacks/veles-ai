# VS Code Start Guide — from fresh Mac to first merged PR

Step-by-step bootstrap for developing **on the MacBook itself** (the server).
One-time setup: ~45 minutes. After that the daily loop is: branch → red test →
green → PR → review → squash merge.

The decisions are baked in — stop re-deciding them:

| Question | Decision | Why |
|---|---|---|
| Where does the repo live? | `~/veles-ai` | §1 |
| Local `git init` first, or GitHub repo first? | **Remote-first** | §3 |
| Which editor, where? | VS Code on the Mac (primary); Win11 laptop via Remote-SSH (secondary) | §2 |
| PR gates + TDD from day one? | Yes — CI, pre-commit and an 85% coverage gate ship in the kit | §5, `docs/pr-tdd-playbook.md` |

## 1. Where everything lives

```
~/veles-ai/           <- the git repo: config, code, docs, tests ONLY
/Volumes/ai-models/   <- GGUF weights (synced from models/models.toml)
/Volumes/ai-state/    <- runtime state: OpenViking data, WebUI data, logs
```

`~/veles-ai` because:

- **Under `$HOME`** — Time Machine covers it by default; no sudo, no
  ownership fights with brew/nix/docker bind mounts.
- **Not** under `~/Desktop`, `~/Documents` or `~/Downloads` — those folders
  can be iCloud-synced: file-eviction placeholders inside `.git`, sync churn
  on every commit, and plaintext-adjacent files drifting into Apple's cloud.
  All three are disqualifying.
- **No spaces in the path** — docker bind mounts, Makefiles and shell
  scripts stay sane.
- Short — you will type this path every day for years.

Alternatives: `~/dev/veles-ai` is fine if you keep a projects root. The
hard constraints are: **under `$HOME`, outside iCloud-synced folders, no
spaces**. Never `/opt` or `/usr/local` (root-owned, wrong conventions for
user-run services).

Heavy artifacts never enter the repo — that is already handled: `.gitignore`
blocks `*.gguf`, models sync to `/Volumes/ai-models`, runtime state lives on
`/Volumes/ai-state` (both APFS-encrypted per `docs/security.md` P1/S10).
Run `chmod 700 ~/veles-ai` after cloning (S2 posture).

## 2. One-time Mac setup (15 min)

```bash
# 1. Xcode Command Line Tools (git + compilers)
xcode-select --install

# 2. Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# ...then paste the two "Next steps" lines it prints at the end

# 3. Tooling
brew install git gh pre-commit uv
brew install --cask visual-studio-code

# 4. VS Code on PATH: launch VS Code -> Cmd+Shift+P ->
#    "Shell Command: Install 'code' command in PATH"
```

Extensions (install once): Python, Pylance, Ruff, GitLens, YAML, Even Better
TOML, Container Tools (Docker), **Cline**, **Continue**.

On-Mac VS Code talks to `http://localhost:4002/v1` (llama-swap) directly —
no Remote-SSH hop, which is the simplest possible loop. Copy
`clients/vscode/` settings for Cline/Continue and fill in your A1 key.
(Remote-SSH from the Win11 laptop remains the *secondary* access path — see
README "VS Code setup". The repo still lives only on the Mac; the laptop
edits it over the tailnet.)

## 3. GitHub first, then local (remote-first — 10 min)

Your instinct was "local `git init` first, push later" — invert it. Remote-first
wins for four reasons:

1. **Branch protection must exist before the direct-push habit does.** If
   you build local history first, your first pushes bypass review and you
   retrofit protection onto an already-formed habit.
2. **CI gates only mean something if they run on your very first PR.**
3. **Secret hygiene is in the first commit** — `.gitignore` + gitleaks are
   on disk before anything risky could be typed, so a key can never reach
   history (rotating a leaked key is a bad way to spend an evening).
4. **Free** — private repos and the Actions free tier cover this project.

The only direct push to `main` you will *ever* make is the bootstrap commit
(branch protection needs `main` to exist first). Everything after is PR-only.

```bash
# 1. SSH key -> GitHub
ssh-keygen -t ed25519 -C "you@example.com"
pbcopy < ~/.ssh/id_ed25519.pub       # github.com > Settings > SSH and GPG keys
ssh -T git@github.com                # smoke test

# 2. Account hardening (security.md P1/S9): passkeys/2FA ON
#    github.com > Settings > Password and authentication
```

In the browser:

1. **New repository** → name `veles-ai` → **Private** → create **empty**
   (no README / .gitignore / license — the kit already has them).
2. **Settings → Branches → Add branch protection rule** for `main`:
   - *Require a pull request before merging* (0 required approvals is
     correct when solo — you cannot approve your own PR anyway);
   - *Require status checks to pass*: `lint`, `test`.
3. Plan note: branch protection on **private** repos needs GitHub Pro
   (~$4/mo). On the free plan the checks still run on every PR — you just
   enforce by discipline until you subscribe. Keeping the repo *public* to
   get free protection is not recommended: infra topology and sops
   ciphertext belong in a private repo.

## 4. Bootstrap the repo (10 min)

```bash
git clone git@github.com:YOU/veles-ai.git ~/veles-ai
cd ~/veles-ai
chmod 700 ~/veles-ai

# copy the starter kit in (everything, including dotfiles).
# Option A - you already extracted the tarball to ~/Downloads/veles-ai-kit/:
cp -R ~/Downloads/veles-ai-kit/. .
# Option B - you kept veles-ai-kit.tar.gz: extract straight into the repo.
# --strip-components=1 drops the wrapper folder so entries land at the
# repo root (NOT in ~/veles-ai/veles-ai-kit/...):
tar -xzf ~/Downloads/veles-ai-kit.tar.gz -C . --strip-components=1

# sanity: ls -A must show .github, .gitignore, .pre-commit-config.yaml,
# .sops.yaml, .yamllint, README.md, clients, docs, models, nix,
# pyproject.toml, requirements-dev.txt, scripts, services, tests

pre-commit install
pre-commit run --all-files    # first run builds hook envs; auto-fixes land

git add -A
git commit -m "chore: bootstrap repo from starter kit (CI + gates + docs)"
git push origin main          # the ONE direct push to main, ever
```

Already created `~/veles-ai` by hand (`mkdir` + `chmod 700`)? Fine —
`git clone` fills an existing **empty** directory. Never run `git init`
inside it yourself: the clone sets up the remote and branch correctly.
If you already ran `git init` (or put files in it), `rm -rf ~/veles-ai`
and let the clone recreate it, then re-run `chmod 700`. Open the folder
in VS Code whenever you like — run the remaining commands in its
integrated terminal (Ctrl+`).

## 5. Daily loop: PR + TDD

```bash
git switch -c feat/first-change
# 1. RED: write the smallest failing test that states the next behavior
pytest -q                         # watch it fail for the RIGHT reason
# 2. GREEN: minimum code to pass
pytest -q
# 3. gates
pytest --cov=services --cov-fail-under=85
pre-commit run --all-files
git commit -m "feat(memory): ..."
git push -u origin feat/first-change
# 4. open the PR (github.com or `gh pr create`), fill the checklist,
#    run the AI review (playbook §3), CI green -> squash-merge, delete branch
```

### Worked example (shipped): the Chapter 14 namespace ACL

`services/memory/nsacl.py` + `tests/memory/test_nsacl.py` implement the
two-level ACL from Ch. 14 — owner-only `viking://users/{principal}/`,
household `viking://family/`, guardian-only delete, deny-by-default for
`viking://system/` — as a pure function with 17 tests at 100% coverage.
Read it first: it is the reference pattern for size (small), shape
(red-green), and naming (test names read as specs).

### Your first PR: `visible_roots` (30 min, do it for real)

The gateway needs "which roots may this principal read?" for merged recall
with provenance (Ch. 14, Listing 14-3). Add to `tests/memory/test_nsacl.py`:

```python
from services.memory.nsacl import visible_roots

def test_visible_roots_own_plus_family():
    assert visible_roots("ben", HOUSEHOLD, GUARDIAN) == [
        "viking://users/ben/",
        "viking://family/",
    ]

def test_visible_roots_unknown_principal_is_empty():
    assert visible_roots("mallory", HOUSEHOLD, GUARDIAN) == []
```

Run `pytest -q` — RED. Now implement `visible_roots(principal, household,
guardian)` in `services/memory/nsacl.py` (own root + family root; unknown
principal → empty list). Green, coverage still 100%, PR, merge. You have
now run the entire loop on a real seam the gateway will consume.

## 6. What gates run where

| Gate | Where | What |
|---|---|---|
| pre-commit (ruff, format, shellcheck, yamllint, gitleaks, private-key) | every local commit | seconds |
| CI `lint` job | every PR | `pre-commit run --all-files` |
| CI `test` job | every PR | pytest + coverage ≥ 85% (bats when present) |
| PR checklist | review | TDD evidence, secrets, egress-ledger row, docs |

`docker compose config -q` and `nix flake check` gates get added in PR 1
once images are pinned (the `<pinned-digest>` placeholders would fail them
today — by design). See playbook §5.

## 7. Troubleshooting

- Weird errors when pasting commands **with their trailing `#` comments**
  (e.g. `chmod: #: No such file or directory`)? Unlike bash, interactive
  zsh does **not** treat `#` as a comment by default — the comment words
  get parsed as arguments. Fix permanently:
  `echo 'setopt interactivecomments' >> ~/.zshrc && source ~/.zshrc`.
  Until then, paste the commands without the comments.
- `pre-commit: command not found` → `brew install pre-commit` (§2).
- `fatal: destination path 'veles-ai' already exists and is not an empty
  directory` → the folder isn't empty (usually a stray `git init`). Move
  any contents aside, delete the folder, clone fresh, re-run `chmod 700`.
- Hooks silently skipped → `pre-commit run --all-files` once manually.
- `gh` auth loops → `gh auth login -p ssh`, prefer the SSH protocol.
- Coverage below 85 → add tests, not waivers. `# pragma: no cover` only for
  glue that needs a live Mac (launchctl, Metal), always with a TODO.
- A secret slipped into a commit → **rotate the key first**, then rewrite
  history (`git filter-repo`); deleting the file in a follow-up commit does
  not remove it from history.
