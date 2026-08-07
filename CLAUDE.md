# TUD Quant — project rules

Student quant finance club at Börsen-Team TU Darmstadt. Repo:
`github.com/TUDQuant/pipeline` (public). Read `ARCHITECTURE.md` before proposing
structural changes; the decisions there were argued for and are not up for
casual revision.

## Audience

The users are 15–30 first- and second-semester students, most of whom have never
used a terminal. Every choice optimises for "works on the first try in a Colab
session" over elegance. If a change makes the code nicer but the onboarding
harder, it is the wrong change.

## The constraint that governs everything

**Colab is the target environment, and it is not configurable.** Its Python
version and its preinstalled numpy/pandas are fixed points; the entire stack is
chosen to fit around them, not the other way round.

Currently: **Python 3.12, numpy 2.0.2, pandas 2.2.2.**

Consequences that have already cost a day each:

- `requires-python` must never exclude Colab's Python. A cap of `<3.12` made the
  package silently uninstallable for every member while passing locally.
- `numpy` and `pandas` are pinned to *exactly* Colab's versions so that
  installing the club package does not upgrade them. An upgrade forces a
  "Restart session" prompt mid-lesson, which is precisely the friction the whole
  design exists to remove.
- `vectorbt` is pinned to 1.0.0 for the same reason - 1.1.0 drags numpy 2.4 and
  pandas 3.0 behind it.
- Verify any dependency change on a throwaway Colab runtime before merging. A
  version that works on a laptop but not in Colab does not work.

## Stack

- Backtesting: `vectorbt` and `backtrader`. **Never write a custom engine.**
- Data: yfinance / Alpha Vantage (equities), ccxt (crypto), FRED (macro)
- Storage: parquet in the `TUD Quant` Google Shared Drive, written nightly by
  GitHub Actions under a club-owned service account

## Commands

```bash
pytest -q                                   # must pass before any commit
ruff check tudquant data-pipelines tests    # must be clean
python scripts/render_notebooks.py          # after ANY change to a .py notebook source
python data-pipelines/update_data.py --group equities --dry-run
```

Local venv setup on Python 3.12 needs setuptools explicitly - 3.12 venvs no
longer ship it, and `pip install -e .` fails with
`Cannot import 'setuptools.build_meta'` without it:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements-pinned.txt && pip install -e .
```

## Hard rules

1. **Never touch credentials.** Do not read, print, echo, or open
   `*service-account*.json`, `.env`, or anything under `_data/`. Do not add
   secrets to any file. If a task appears to need a secret, stop and say so.
2. **Never commit `.ipynb` outside `colab/`.** Notebooks are `.py` in jupytext
   percent format. See `docs/notebooks.md`. CI enforces this.
3. **Never unpin a dependency** in `requirements-pinned.txt` without being asked
   explicitly, and never without testing on Colab first.
4. **Never widen the data universe** in `data-pipelines/universe.yml` without
   being asked. Every symbol is a nightly API call and a file every member syncs.
5. **No new runtime dependencies** without flagging it first. Every dependency is
   something that can fail in a Colab cell in front of a room of people.

## Conventions

- Config lives only in `tudquant/config.py`. No path is hardcoded anywhere else -
  this is what keeps the Phase 2 move to JupyterHub a migration and not a rewrite.
- The Shared Drive data folder is **`Data`**, capital D. Colab's Drive mount is
  case-sensitive even though macOS is not, so `config.py` probes both spellings
  rather than assuming.
- Every data source adapter returns a `DatetimeIndex` named `date` and lowercase
  columns: `open, high, low, close, volume` (+ `adj_close` where available).
- New validation checks go in `tudquant/validation.py` and get a test in
  `tests/test_validation.py` that injects the fault and asserts it is caught. A
  quality check without a test that proves it fires is decoration.
- Member-facing errors must say what to do next, not just what went wrong.
- A check that cannot run in a member's session and *should not* run there
  raises `NotApplicable`, so it reports SKIP rather than FAIL. Members who see
  red for something that was never meant to work learn to ignore the summary.

## Shipping a change

`main` is protected. A push to `main` is rejected; everything goes through a PR:

```bash
git checkout -b fix/thing
# edit, then if a notebook source changed:
python scripts/render_notebooks.py
git add -A && git commit -m "..." && git push origin fix/thing
gh pr create --fill
gh pr checks --watch          # required check is named "test"
gh pr merge --squash --delete-branch
git checkout main && git pull origin main
```

**A pushed branch is not a shipped change.** Colab reads `main`. Until the PR is
merged and `git pull` shows it locally, nothing you did has reached a member.
This has been mistaken for a bug three separate times.

## When writing curriculum

Use the `tudquant-lesson` skill in `.claude/skills/`. Lessons are pedagogical
artefacts, not demos - the guidance there is not optional formatting advice.
