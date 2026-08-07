# Troubleshooting

Symptoms seen at least once, with the cause. Roughly in order of how likely you
are to hit them.

---

## "data directory not found" for one member

They are not a **member** of the `TUD Quant` Shared Drive. Sharing the `Data`
folder with them is not the same thing and does not work: Colab exposes
`/content/drive/Shareddrives/<name>` only for Shared Drives the user belongs to.
A shared folder lands under "Shared with me", at a path Colab does not surface.

Fix: Shared Drive → *Manage members* → add them → **Viewer**. See `SETUP.md` §5.

Also check they signed in with the club account and not a private Gmail.

## Everything fails for everyone after a dependency change

Almost certainly the package no longer installs on Colab. The usual cause is a
version constraint that excludes Colab's Python or forces a numpy/pandas upgrade.

Check the bootstrap cell output for a pip error, and reread the Colab section of
`CLAUDE.md`. Local tests passing is not evidence — an earlier stack passed all 11
smoke checks on a laptop while being uninstallable for every member.

## `colab/` notebooks are stale — the `.py` changed but the `.ipynb` didn't

Either `python scripts/render_notebooks.py` was not run, or the PR was pushed but
never merged. Colab reads `main`.

```bash
git log --oneline -3 -- colab/
```

If the top commit is old, that is your answer.

## Colab shows old content even after merging

Colab caches the opened notebook. Reopen via File → Open notebook → GitHub —
not from Recent, not the existing tab. Also Runtime → Disconnect and delete
runtime, because the previously installed `tudquant` makes the bootstrap's
`find_spec` check skip reinstalling.

## PR cannot be merged, no checks reported

The head commit has no CI run. If something pushed to the branch without
triggering a workflow (anything authenticated with `GITHUB_TOKEN` does this),
push a commit of your own to trigger one.

If checks *are* reported but the ruleset still blocks, verify the required check
is named **`test`**, not `ci`. GitHub matches the job name.

## Push to `main` rejected with GH013

Working as intended. Branch protection. Use a branch and a PR.

## `pip install -e .` fails with `Cannot import 'setuptools.build_meta'`

Python 3.12 venvs do not ship setuptools:

```bash
pip install --upgrade pip setuptools wheel
```

## Nightly pipeline green but a dataset is stale

Check which source served it. Binance blocks datacenter IP ranges and GitHub
Actions runners sit in them, so `ccxt` falls back to Kraken then Coinbase
silently. Equities can fall back from yfinance to Alpha Vantage, whose free tier
is very tight.

```bash
gh run view <run-id> --log | grep -A5 "== equities =="
```

## A member's backtest shows an implausible return

Have them run `data.quality(symbol, source)` before anything else. An unadjusted
split produces exactly this. If the quality report is clean, the next suspects
are lookahead bias and survivorship — both curriculum topics, not bugs.

## Smoke test shows FRED as SKIP

Correct. Club API keys live in the nightly pipeline, never in a member session;
macro data reaches members through the cache. A SKIP is not a failure.
