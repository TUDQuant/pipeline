# TUD Quant — infrastructure design

Status: **Phase 1 built and running** · Owner: infrastructure · Repo: `TUDQuant/pipeline`

---

## The decision in one paragraph

A member gets a club Workspace account, opens a Colab notebook, runs one cell,
and has the club library plus ~17 cleaned, validated market datasets. No install,
no token, no manual step. Behind that, GitHub Actions refreshes the data nightly
and writes parquet into a Google Shared Drive. Nothing runs on a server we pay
for or maintain. When free-tier Colab becomes the binding constraint — and it
will — the same code moves to JupyterHub by changing one environment variable.

## Why not go straight to JupyterHub

Standing up Docker, a VM, OAuth and IAM before a single lesson exists is effort
spent on infrastructure with no users, at the moment curriculum is the scarce
resource. And the first session is where members are lost: a room of
first-semesters installing Python on mixed Windows laptops loses the hour and a
third of the cohort. Colab removes that entirely.

## Why not stay on Colab forever

Free-tier Colab gives ~12GB RAM, no persistence, and sessions that idle out.
Enough for daily bars and the first semester. Not enough for parameter sweeps
over minute data, and there is no shared compute or scheduling. The move is a
question of when, not whether.

## Architecture

```
  GitHub Actions (nightly cron)
        │  fetch → validate → parquet
        ▼
  Shared Drive: TUD Quant/Data/
        ├── parquet/   cleaned datasets
        └── quality/   one JSON report per dataset
        │
        │  mounted read-only (Viewer)
        ▼
  Member's Colab session
        └── one bootstrap cell → data.equities("AAPL")
```

Three pieces, all free: **Colab** for member compute, **GitHub** for code and
scheduling, **Drive** for the data layer.

The scheduling piece was not in the original discussion and matters most. Colab
cannot run anything on a schedule — no persistent runtime, sessions die. Without
Actions there is no automated pulling and cleaning at all, and every member ends
up calling the same API from their own notebook and hitting rate limits by week
two.

## What makes Phase 2 a migration and not a rewrite

1. **One config point.** `tudquant/config.py` is the only module that knows where
   data lives. Colab resolves to the Drive mount; a server resolves to
   `/srv/tudquant/data`; `TUDQUANT_DATA_ROOT` overrides both.
2. **One data interface.** Members write `data.equities("AAPL")`. Whether that
   reads a mounted Drive or a local volume is invisible. No curriculum notebook
   changes on migration.
3. **One pinned environment.** `requirements-pinned.txt` is what Colab installs
   today and what the Docker image will install later.
4. **`bootstrap()` is environment-aware.** It mounts Drive on Colab and does
   nothing on a server. The member-facing cell is byte-identical in both worlds.

## The stack is dictated by Colab

This is the single most important constraint and the one that cost the most to
learn. Colab's Python version and preinstalled numpy/pandas cannot be changed by
us, so everything else is chosen to fit around them: **Python 3.12, numpy 2.0.2,
pandas 2.2.2, vectorbt 1.0.0.**

numpy and pandas are pinned to *exactly* Colab's versions so that installing the
club package does not upgrade them — an upgrade forces a session restart
mid-lesson. vectorbt 1.0.0 is the newest release that holds that property.

An earlier stack (Python 3.10, numpy 1.23.5, vectorbt 0.26.2) worked perfectly on
a laptop and was **uninstallable on Colab**, because `requires-python` capped
below 3.12. It passed every local test while being broken for every member. The
lesson generalises: local success is not evidence.

## Data quality

The pipeline validates every dataset nightly and stores a report beside it.
Checks: duplicate or unsorted timestamps, non-positive prices, OHLC violations,
missing sessions against a business or daily calendar, unadjusted splits (a jump
near a common ratio), erratic adjustment factors, stale feeds.

Reading a dataset that failed prints a warning naming the specific problem.
`data.check(df)` runs the same checks on anything a member builds themselves.

This exists because a member who backtests a series with an unadjusted 2:1 split
sees a spectacular return that never existed, and learns something false with
high confidence. Detecting that is cheap; the alternative is teaching people to
trust numbers they cannot check.

## Fixed choices

| Choice | Rationale |
|---|---|
| yfinance / Alpha Vantage, ccxt, FRED | What the field actually uses; free tiers sufficient for daily bars |
| VectorBT + Backtrader | Both mature; a club-built engine would be worse and cost the semester |
| Public repos | One-line install with no per-member token; free branch protection; visible for recruiting |
| Notebooks committed as `.py` | See [`docs/notebooks.md`](docs/notebooks.md) |
| CI verifies `colab/`, never generates it | See below |
| Sheets + GOOGLEFINANCE | Onboarding dashboard for non-technical members only. Never pipeline input — gappy history, undocumented changes, unreliable intraday |

### Why CI verifies notebooks instead of generating them

Two earlier designs failed against real GitHub constraints, and both failures
were silent:

1. A bot pushing generated notebooks to `main` is blocked by branch protection,
   and GitHub Actions is not an available bypass actor.
2. A bot pushing to the PR branch instead does not trigger a CI run — pushes
   authenticated with `GITHUB_TOKEN` never do — so the required status check
   never reports on the new head commit and the PR becomes unmergeable.

The working design removes the bot: contributors run
`python scripts/render_notebooks.py` locally, and CI re-renders and fails if the
committed output differs. This needs deterministic rendering, which plain
jupytext does not provide (nbformat 4.5 assigns random cell IDs), hence the
script.

## Open items

- **Intraday data.** Everything here is daily. If curriculum needs intraday or
  tick data, no free source covers it and that becomes a budget decision.
- **Colab tier.** Built for the free tier. Pro/Pro+ would push Phase 2 well past
  the first semester and widen what curriculum can cover.
- **Second infrastructure owner.** Currently one person, which is why required
  PR approvals are set to 0. That is a gap, not a preference.

## What is deliberately not built

No custom backtesting engine. No self-hosted database. No web dashboard. No
Phase 2 infrastructure. Each is a reasonable thing to want and a bad thing to
build before there are members using what exists.
