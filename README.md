# TUD Quant

Code, curriculum and data for the quantitative finance program at Börsen-Team TU Darmstadt.

## Start here (new members)

You need nothing installed. No Python, no terminal, no Anaconda.

1. Sign in to Google with your **club account** (`vorname.nachname@…`). Not your private Gmail — the shared data lives on a Drive only club accounts can see.
2. Open [`colab/00_welcome.ipynb`](colab/) and click **Open in Colab**.
3. Run the first cell. Approve the Drive prompt when it appears.
4. You now have the club library and roughly 20 cleaned market datasets. Go.

If a cell fails, run [`colab/smoke_test.ipynb`](colab/) and post the output in the infrastructure channel. It tells us exactly which piece broke.

## The one setup cell

Every club notebook starts with this and nothing else:

```python
!pip install -q "tudquant[backtest] @ git+https://github.com/TUDQuant/pipeline.git@main"
import tudquant; tudquant.bootstrap()
```

## Getting data

```python
from tudquant import data

px  = data.equities("AAPL")        # daily OHLCV, split-adjusted, from cache
btc = data.crypto("BTC/USDT")
y10 = data.macro("DGS10")

data.catalogue()                   # everything available right now
```

Data comes from the nightly cache, not from a live API call. That is deliberate: thirty members each calling Alpha Vantage would exhaust the free tier before the session ended. If you need a symbol we don't carry, open an issue and we add it to `data-pipelines/universe.yml`.

### Data quality is not assumed

Every dataset is validated nightly — gaps, unadjusted splits, impossible OHLC, stale feeds. If a series failed, reading it prints a warning:

```python
data.quality("AAPL", "equities")   # the full report
data.check(my_dataframe)           # validate something you built yourself
```

**Read the warning.** A backtest on a series with an unadjusted split will show a fantastic strategy that never existed. Finding that out yourself, once, is a useful lesson; publishing it to the club is not.

## Repository layout

| Path | What it is | Who owns it |
|---|---|---|
| `tudquant/` | The installable club library: data access, caching, validation | Infrastructure |
| `data-pipelines/` | Nightly GitHub Actions jobs that build the cache | Infrastructure |
| `curriculum/` | Lesson notebooks, as `.py` | Curriculum team |
| `strategies/` | Member strategy work | Members |
| `colab/` | **Generated.** Never edit — CI rebuilds it from `curriculum/` | Nobody |
| `notebooks/` | Smoke test and templates | Infrastructure |

## Contributing a notebook

Notebooks are committed as **`.py` files**, not `.ipynb`. CI will reject a stray `.ipynb`. See [`docs/notebooks.md`](docs/notebooks.md) for the thirty-second version of why and how.

```bash
jupytext --to py:percent my_notebook.ipynb     # before you commit
```

## Backtesting

Use `vectorbt` for fast vectorised sweeps and `backtrader` for event-driven logic with realistic order handling. We do not write our own engine — both of these are better than anything we would build, and the time is better spent on strategy and statistics.

## Setting this up from scratch

See [`SETUP.md`](SETUP.md). You should not need it unless you are taking over infrastructure.
