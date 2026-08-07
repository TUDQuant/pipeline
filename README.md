# TUD Quant

Code, curriculum and data for the quantitative finance program at Börsen-Team
TU Darmstadt.

## Start here (new members)

You need nothing installed. No Python, no terminal, no Anaconda.

1. Sign in to Google with your **club account** (`vorname.nachname@boersen-team.de`).
   Not a private Gmail — the shared data lives on a Drive only club accounts can see.
2. Ask infrastructure to add you to the **`TUD Quant` Shared Drive** if they
   haven't already. Without membership the data folder will not appear.
3. Open [`colab/00_welcome.ipynb`](colab/) — in Colab: File → Open notebook →
   GitHub → `TUDQuant/pipeline`.
4. Run the first cell. Approve the Drive prompt when it appears.

You now have the club library and ~17 cleaned market datasets. Go.

If a cell fails, run [`colab/smoke_test.ipynb`](colab/) and post the output in
the infrastructure channel. It tells us exactly which piece broke. FRED showing
SKIP is normal — club API keys never live in a member session.

## The one setup cell

Every club notebook starts with this and nothing else:

```python
import importlib.util, subprocess, sys

PACKAGE = "tudquant[backtest] @ git+https://github.com/TUDQuant/pipeline.git@main"
if importlib.util.find_spec("tudquant") is None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", PACKAGE], check=True)

import tudquant
cfg = tudquant.bootstrap()
```

## Getting data

```python
from tudquant import data

px  = data.equities("AAPL")        # daily OHLCV, split-adjusted, from cache
btc = data.crypto("BTC/USDT")
y10 = data.macro("DGS10")

data.catalogue()                   # everything available right now
```

Data comes from the nightly cache, not from a live API call. That is deliberate:
thirty members each calling Alpha Vantage would exhaust the free tier before the
session ended. Need a symbol we don't carry? Open an issue and we add it to
`data-pipelines/universe.yml`.

### Data quality is not assumed

Every dataset is validated nightly — gaps, unadjusted splits, impossible OHLC,
stale feeds. If a series failed, reading it prints a warning:

```python
data.quality("AAPL", "equities")   # the full report
data.check(my_dataframe)           # validate something you built yourself
```

**Read the warning.** A backtest on a series with an unadjusted split will show a
fantastic strategy that never existed. Finding that out yourself once is a useful
lesson; publishing it to the club is not.

## Repository layout

| Path | What it is | Who owns it |
|---|---|---|
| `tudquant/` | The installable club library: data access, caching, validation | Infrastructure |
| `data-pipelines/` | Nightly GitHub Actions jobs that build the cache | Infrastructure |
| `curriculum/` | Lesson notebooks, as `.py` | Curriculum team |
| `strategies/` | Member strategy work | Members |
| `colab/` | **Generated.** Never edit by hand — see below | Nobody |
| `notebooks/` | Smoke test and templates | Infrastructure |
| `scripts/` | `render_notebooks.py` | Infrastructure |

## Contributing

Notebooks are committed as **`.py` files**, not `.ipynb`. After changing any
notebook source:

```bash
python scripts/render_notebooks.py
```

CI verifies `colab/` matches the sources and fails the PR if it doesn't. See
[`docs/notebooks.md`](docs/notebooks.md) for why.

`main` is protected — work on a branch and open a PR. And note that merging is a
separate step from pushing: Colab reads `main`, so nothing reaches a member until
the PR is merged.

## Backtesting

`vectorbt` for fast vectorised sweeps, `backtrader` for event-driven logic with
realistic order handling. We do not write our own engine — both are better than
anything we would build, and the time is better spent on strategy and statistics.

## Setting this up from scratch

See [`SETUP.md`](SETUP.md), which also covers weekly operations and member
onboarding. You should not need it unless you are taking over infrastructure.
