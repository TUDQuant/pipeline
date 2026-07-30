# TUD Quant — infrastructure design

Status: proposed for Phase 1 · Owner: infrastructure · Deadline: semester start

---

## The decision in one paragraph

Members get a club Workspace account, open a Colab notebook, run one cell, and have the club library plus roughly twenty cleaned, validated market datasets. No install, no token, no manual step. Behind that, GitHub Actions refreshes the data nightly and writes parquet into a Shared Drive. Nothing runs on a server we pay for or maintain. When free-tier Colab becomes the binding constraint — and it will — the same code moves to JupyterHub by changing one environment variable.

## Why not go straight to JupyterHub

Because Marven is right about sequencing. Standing up Docker, a VM, OAuth and IAM before a single lesson exists is effort spent on infrastructure that has no users yet, at the exact moment curriculum is the scarce resource. And the first session is where members are lost: a room of first-semesters installing Python on mixed Windows laptops loses the hour and a third of the cohort.

So Phase 1 is free-tier and ships now. But it is built so Phase 2 is a migration rather than a rewrite — see below.

## Why not stay on Colab forever

Free-tier Colab gives about 12GB of RAM, no persistence, and sessions that idle out. That is enough for daily bars and the first semester of curriculum. It is not enough for parameter sweeps over minute data, and there is no shared compute or scheduling. The move is a question of when, not whether.

## Architecture

```
  GitHub Actions (nightly cron)
        │  fetch → validate → parquet
        ▼
  Shared Drive: TUD Quant/data/
        ├── parquet/   cleaned datasets
        └── quality/   one JSON report per dataset
        │
        │  mounted read-only
        ▼
  Member's Colab session
        └── pip install tudquant → data.equities("AAPL")
```

Three pieces, all free: **Colab** for member compute, **GitHub** for code and scheduling, **Drive** for the data layer.

The scheduling piece is the one that wasn't in the original discussion and matters. Colab cannot run anything on a schedule — no persistent runtime, sessions die. Without Actions there is no "automated pulling and cleaning" at all, and every member ends up calling the same API from their own notebook and hitting rate limits by week two.

## What makes Phase 2 a migration and not a rewrite

Four commitments, all already in the code:

1. **One config point.** `tudquant/config.py` is the only module that knows where data lives. Colab resolves to the Drive mount; a server resolves to `/srv/tudquant/data`; `TUDQUANT_DATA_ROOT` overrides both. Nothing else in the package contains a path.
2. **One data interface.** Members write `data.equities("AAPL")`. Whether that reads a mounted Drive or a local volume is invisible to them. No curriculum notebook changes on migration.
3. **One pinned environment.** `requirements-pinned.txt` is what Colab installs today and what the Docker image will install later. Same versions, same behaviour.
4. **`bootstrap()` is environment-aware.** It mounts Drive on Colab and does nothing on a server. The member-facing cell is byte-identical in both worlds.

The migration is then: build an image from the pins, point `TUDQUANT_DATA_ROOT` at a volume, sync the parquet directory once. Curriculum is untouched.

## Data quality

The pipeline validates every dataset nightly and stores a report next to it. Checks: duplicate or unsorted timestamps, non-positive prices, OHLC violations, missing sessions against a business or daily calendar, unadjusted splits (a jump near a common ratio), erratic adjustment factors, and stale feeds.

Reading a dataset that failed prints a warning naming the specific problem.

This exists because of Marven's point about pedagogical danger, and it is the right point. A member who backtests a series with an unadjusted 2:1 split sees a strategy with a spectacular return that never existed, and learns something false with high confidence. Detecting that is cheap; the alternative is teaching people to trust numbers they cannot check.

`data.check(df)` runs the same checks on anything a member builds themselves.

## Fixed choices

| Choice | Rationale |
|---|---|
| yfinance / Alpha Vantage, ccxt, FRED | What the field actually uses; free tiers sufficient for daily bars |
| VectorBT + Backtrader | Both mature; a club-built engine would be worse and cost the semester |
| Public repos | One-line install with no per-member token; free branch protection; visible for recruiting |
| Notebooks committed as `.py` | See [`docs/notebooks.md`](docs/notebooks.md) |
| Sheets + GOOGLEFINANCE | Onboarding dashboard for non-technical members only. Never pipeline input — gappy history, undocumented changes, unreliable intraday |

## Open items

- **Intraday data.** Everything here is daily. If curriculum needs intraday or tick data, no free source covers it and that becomes a budget decision. Better surfaced now than in week six.
- **Colab tier.** Built for the free tier. Pro/Pro+ would push Phase 2 well past the first semester and widen what curriculum can cover.
- **Drive quota.** Fine at 15–30 members and ~20 daily datasets. Revisit if the universe grows past a few hundred symbols.

## What is deliberately not built

No custom backtesting engine. No self-hosted database. No web dashboard. No Phase 2 infrastructure. Each of these is a reasonable thing to want and a bad thing to build before there are members using the thing that exists.
