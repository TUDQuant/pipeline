# Changing the repo, from zero

How to get a change from your laptop onto `main`, which is what every member's
Colab session reads.

**You only need this if you are changing code, curriculum or data config.**
Members who just *use* the environment need a club Google account and Colab,
nothing here — see the README.

---

## 1. Who is allowed to do what

| Who | Can do | How they get it |
|---|---|---|
| Anyone on the internet | Read and clone (the repo is public) | Nothing needed |
| Club member in a GitHub team (`members`, `curriculum`) | Push branches, open pull requests | Org invite from Noam |
| `infrastructure` team (Noam + backup) | Above, plus repo settings, secrets, rulesets | Admin role |
| **Nobody** | Push directly to `main` | — `main` is protected |

Every change reaches `main` the same way: **branch → pull request → CI passes →
merge.** There is no shortcut, and you should not want one: CI is what stops a
broken change reaching twenty people in a session.

Someone outside the org can still contribute: fork the repo on GitHub, push to
the fork, open a PR from there. Same review, same CI.

### Getting added

1. Create a GitHub account at https://github.com/signup if you have none. A
   personal account is fine — it stays yours after you leave the club.
2. Send Noam your GitHub username.
3. Accept the invitation email from GitHub ("You've been invited to join
   TUDQuant"). Until you accept, you are not a member and pushes are refused.

---

## 2. One-time setup on your laptop

Instructions are for macOS. On Windows, use Git for Windows, `winget install
GitHub.cli` and the python.org installer, then the same commands in Git Bash.

### Install the tools

```bash
xcode-select --install          # git; skip if `git --version` already works
brew install gh python@3.12     # GitHub CLI and Python 3.12
```

No Homebrew? Install it from https://brew.sh first.

Python must be **3.12**. That is what Colab runs, and the dependency pins are
built around it. 3.13+ or 3.10 will give you install errors that have nothing to
do with your change.

### Log in to GitHub

```bash
gh auth login
```

Answer the prompts like this:

```
? Where do you use GitHub?                       GitHub.com
? What is your preferred protocol for Git operations?   HTTPS
? Authenticate Git with your GitHub credentials? Yes
? How would you like to authenticate GitHub CLI? Login with a web browser

! First copy your one-time code: XXXX-XXXX
Press Enter to open https://github.com/login/device in your browser...
```

Paste the code in the browser, approve, and you should see:

```
✓ Authentication complete.
✓ Logged in as <your-username>
```

**Do not use your GitHub password with git.** GitHub disabled password
authentication for git years ago; `git clone` with a password fails even when the
password is correct. `gh auth login` sets up a token for you instead.

### Tell git who you are

This name is what appears on your commits in the club's history.

```bash
git config --global user.name  "Vorname Nachname"
git config --global user.email "you@example.com"   # an address on your GitHub account
```

### Get the code

Put it somewhere permanent — not `Downloads`.

```bash
mkdir -p ~/Projects
gh repo clone TUDQuant/pipeline ~/Projects/tud-quant
cd ~/Projects/tud-quant
```

### Create the Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel     # 3.12 venvs ship without setuptools
pip install -r requirements-pinned.txt
pip install -e ".[dev]"
```

Check it:

```bash
pytest -q
```

You should see `17 passed` (or more — never fewer). Your prompt now starts with
`(.venv)`; run `source .venv/bin/activate` again in every new terminal.

---

## 3. Making a change

The same loop every time. Expected output is shown under each step so you can
tell immediately if something is off.

### a. Start from an up-to-date main

```bash
cd ~/Projects/tud-quant
source .venv/bin/activate
git checkout main
git pull origin main
```
```
Already on 'main'
Already up to date.         ← or a list of files that changed; both are fine
```

### b. Make a branch

Name it after what you are doing.

```bash
git checkout -b add-sap-to-universe
```
```
Switched to a new branch 'add-sap-to-universe'
```

### c. Edit, then check locally

Edit the files. Then:

```bash
pytest -q                                   # must pass
ruff check tudquant data-pipelines tests    # must say "All checks passed!"
```

**If you changed anything in `curriculum/` or `notebooks/`**, also:

```bash
python scripts/render_notebooks.py
```
```
rendered colab/00_welcome.ipynb
rendered colab/smoke_test.ipynb
```

CI fails the PR if you forget — the `.ipynb` files members open in Colab are
generated from the `.py` sources, and must match them.

### d. Look before you commit

```bash
git status
```

Read the list. You should see only files you meant to change. If you see
`.venv/`, `.DS_Store`, `__pycache__/` or anything ending in `.json` that looks
like a key — **stop**, do not commit, ask in the infrastructure channel.

### e. Commit and push the branch

```bash
git add -A
git commit -m "Add SAP to the equity universe"
git push origin add-sap-to-universe
```
```
 * [new branch]      add-sap-to-universe -> add-sap-to-universe
```

### f. Open the pull request

```bash
gh pr create --fill
```
```
https://github.com/TUDQuant/pipeline/pull/12
```

### g. Wait for CI

GitHub needs a few seconds to register the run, so wait before watching:

```bash
sleep 30
gh pr checks --watch
```
```
✓  ci/test (pull_request)    1m25s
All checks were successful
```

Takes about 1.5 minutes. Red? See **Troubleshooting** below — do not merge.

### h. Merge, then come back to main

```bash
gh pr merge --squash --delete-branch
git checkout main
git pull origin main
```
```
✓ Squashed and merged pull request TUDQuant/pipeline#12
✓ Deleted local branch add-sap-to-universe and switched to branch main
```

**Your change is live only after this step.** A pushed branch, or an open PR,
has not reached anyone. Colab installs the club package from `main`.

### i. Confirm it worked

For code or curriculum changes, open `colab/smoke_test.ipynb` in a **fresh**
Colab runtime (File → Open notebook → GitHub → `TUDQuant/pipeline`; then Runtime
→ Disconnect and delete runtime, and run all). Everything should be PASS, with
FRED as SKIP.

For data changes, see [`data-universe.md`](data-universe.md).

---

## 4. Troubleshooting

Every one of these has happened at least once.

| You see | What it means | Do this |
|---|---|---|
| `fatal: not a git repository` | You are not inside the repo folder | `cd ~/Projects/tud-quant` |
| `zsh: command not found: gh` | GitHub CLI not installed | `brew install gh`, then `gh auth login` |
| `Password authentication is not supported` / clone fails with right password | Git no longer accepts passwords | `gh auth login` (section 2) |
| `Permission to TUDQuant/pipeline denied` / `403` on push | Not an org member yet, or invite not accepted | Check email for the invite; ask Noam |
| `GH013: Repository rule violations` … `Changes must be made through a pull request` | You pushed to `main` | Normal. `git checkout -b my-branch`, then push that branch |
| `! [rejected] main -> main (non-fast-forward)` / `fetch first` | Someone merged since you last pulled | `git pull --rebase origin main`, then push again |
| `no checks reported on the '...' branch` | You asked too fast | `sleep 30` and run `gh pr checks --watch` again |
| `is not mergeable: the base branch policy prohibits the merge` | CI hasn't passed (yet, or at all) | `gh pr checks` — wait, or fix what is red |
| CI red at **Verify colab/ matches the sources** | Notebook source changed, `colab/` not re-rendered | `python scripts/render_notebooks.py`, commit, push |
| CI red at **Lint** | Style issue | `ruff check --fix tudquant data-pipelines tests`, commit, push |
| CI red at **Unit tests** | Your change broke something | Run `pytest -q` locally and read the failure |
| CI red at **Smoke test (offline)** on a PR that touched nothing relevant | A dependency released a breaking version | Tell infrastructure; it affects everyone, not just you |
| `Cannot import 'setuptools.build_meta'` | Fresh 3.12 venv | `pip install --upgrade pip setuptools wheel` |
| `ResolutionImpossible` / pip builds numpy from source | Wrong Python version | `python --version` must say 3.12 — recreate the venv |
| `Your name and email address were configured automatically` | git identity not set | Run the two `git config --global` lines in section 2 |
| You committed on the wrong branch | Happens to everyone | `git branch fix-it` (saves your commit), `git checkout main`, `git reset --hard origin/main`, `git checkout fix-it` |
| Change merged but Colab still shows the old version | Colab cached the notebook, or the old package is still installed | Reopen from GitHub (not Recent), and Runtime → Disconnect and delete runtime |

### Never

- `git push --force` to `main`, or `gh pr merge --admin`. Both exist to bypass
  the protection that keeps sessions working.
- Commit `.ipynb` files outside `colab/`, or anything that looks like a key.
- Edit files in GitHub's web editor and on your laptop at the same time — the two
  copies drift and one silently undoes the other.
