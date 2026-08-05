# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # TUD Quant — environment smoke test
#
# Run this top to bottom. Every component prints PASS, FAIL or SKIP.
# If anything says FAIL, do not start the lesson — post the output in the
# infrastructure channel and we fix it before twenty people hit the same wall.
#
# This same file runs in CI on every pull request with `TUDQUANT_SMOKE_OFFLINE=1`,
# which skips the live network checks.

# %%
# --- bootstrap: the only setup cell any club notebook ever needs -------------
import importlib.util
import subprocess
import sys

PACKAGE = "tudquant[backtest] @ git+https://github.com/TUDQuant/pipeline.git@main"

if importlib.util.find_spec("tudquant") is None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", PACKAGE], check=True)

import tudquant

cfg = tudquant.bootstrap()

# %%
import os
import time
import traceback

OFFLINE = os.environ.get("TUDQUANT_SMOKE_OFFLINE") == "1"

RESULTS = []


def check(name, fn, skip_if_offline=False):
    """Run one component check. Never raises — we want the full picture."""
    if skip_if_offline and OFFLINE:
        RESULTS.append((name, "SKIP", "offline mode"))
        print(f"SKIP  {name}")
        return None

    started = time.time()
    try:
        detail = fn()
        elapsed = time.time() - started
        RESULTS.append((name, "PASS", f"{detail} [{elapsed:.1f}s]"))
        print(f"PASS  {name}: {detail}")
        return detail
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((name, "FAIL", f"{type(exc).__name__}: {exc}"))
        print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
        if os.environ.get("TUDQUANT_SMOKE_VERBOSE"):
            traceback.print_exc()
        return None


# %% [markdown]
# ## 1. Package and environment

# %%
def _package():
    from tudquant import data  # noqa: F401

    return f"tudquant {tudquant.__version__}, env={cfg.environment}"


def _versions():
    import numpy
    import pandas

    return f"numpy {numpy.__version__}, pandas {pandas.__version__}"


check("package import", _package)
check("core versions", _versions)

# %% [markdown]
# ## 2. Data directory (Drive in Colab, volume on the server)

# %%
from pathlib import Path

from tudquant import cache


def _data_root():
    if not cache.available():
        raise RuntimeError(
            f"{cfg.data_root} not reachable. In Colab: add the 'TUD Quant' "
            "Shared Drive to your Drive, then re-run bootstrap()."
        )
    return str(cfg.data_root)


def _cache_write():
    import pandas as pd

    # Deliberately does NOT create the directory. If it is missing that is the
    # failure we want to see, not something to paper over by making an empty
    # folder next to the real one.
    if not cfg.cache_dir.parent.is_dir():
        raise RuntimeError(f"{cfg.data_root} does not exist - not writing a probe into it")

    probe = Path(cfg.data_root) / "_smoke_probe.parquet"
    pd.DataFrame({"x": [1, 2, 3]}).to_parquet(probe)
    back = pd.read_parquet(probe)
    probe.unlink()
    return f"read/write ok ({len(back)} rows)"


def _catalogue():
    from tudquant import data

    cat = data.catalogue()
    if cat.empty:
        raise RuntimeError("cache is empty — has the nightly pipeline run yet?")
    bad = int((~cat["ok"].fillna(True)).sum())
    return f"{len(cat)} datasets cached, {bad} failing quality"


check("data directory", _data_root, skip_if_offline=True)
check("cache read/write", _cache_write, skip_if_offline=True)
check("catalogue", _catalogue, skip_if_offline=True)

# %% [markdown]
# ## 3. Live data sources
#
# Members normally read the cache. These check that the *pipeline's* sources
# still work, which is how we find out yfinance broke before a lesson does.

# %%
from tudquant import data


def _yf():
    df = data.fetch_live("AAPL", "equities", start="2024-01-01")
    return f"{len(df)} rows, last {df.index[-1].date()}"


def _ccxt():
    df = data.fetch_live("BTC/USDT", "crypto", start="2024-06-01")
    return f"{len(df)} rows, last {df.index[-1].date()}"


def _fred():
    if not os.environ.get("FRED_API_KEY"):
        raise RuntimeError("no FRED key in this session (expected for members)")
    df = data.fetch_live("DGS10", "macro", start="2024-01-01")
    return f"{len(df)} rows"


check("yfinance (equities)", _yf, skip_if_offline=True)
check("ccxt (crypto)", _ccxt, skip_if_offline=True)
check("FRED (macro)", _fred, skip_if_offline=True)

# %% [markdown]
# ## 4. Validation layer

# %%
def _validation():
    import numpy as np
    import pandas as pd

    idx = pd.bdate_range("2024-01-01", periods=60)
    px = pd.Series(np.linspace(100, 120, 60), index=idx)
    df = pd.DataFrame(
        {"open": px, "high": px * 1.01, "low": px * 0.99, "close": px, "volume": 1e6}
    )
    # Inject an unadjusted 2:1 split so the checker has something to find.
    df.loc[idx[30]:, ["open", "high", "low", "close"]] /= 2

    report = data.check(df, "SMOKE", "equities")
    if report.ok:
        raise RuntimeError("validator missed an injected split — this is a real bug")
    return f"caught {len(report.errors)} errors as expected"


check("validation layer", _validation)

# %% [markdown]
# ## 5. Backtesting engines

# %%
def _vectorbt():
    import numpy as np
    import pandas as pd
    import vectorbt as vbt

    idx = pd.bdate_range("2023-01-01", periods=250)
    rng = np.random.default_rng(0)
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 250))), index=idx)

    fast, slow = px.rolling(10).mean(), px.rolling(30).mean()
    pf = vbt.Portfolio.from_signals(px, fast > slow, fast < slow, init_cash=10_000)
    return f"total return {pf.total_return():.2%}"


def _backtrader():
    import backtrader as bt
    import numpy as np
    import pandas as pd

    idx = pd.bdate_range("2023-01-01", periods=250)
    rng = np.random.default_rng(0)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 250)))
    df = pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99,
         "close": close, "volume": 1e6}, index=idx
    )

    class SMA(bt.Strategy):
        def __init__(self):
            self.sma = bt.indicators.SMA(self.data.close, period=20)

        def next(self):
            if not self.position and self.data.close[0] > self.sma[0]:
                self.buy()
            elif self.position and self.data.close[0] < self.sma[0]:
                self.close()

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(bt.feeds.PandasData(dataname=df))
    cerebro.addstrategy(SMA)
    cerebro.broker.setcash(10_000)
    cerebro.run()
    return f"final value {cerebro.broker.getvalue():,.0f}"


check("vectorbt", _vectorbt)
check("backtrader", _backtrader)

# %% [markdown]
# ## Summary

# %%
import pandas as pd

summary = pd.DataFrame(RESULTS, columns=["component", "status", "detail"])
failed = summary[summary.status == "FAIL"]

print("\n" + "=" * 64)
print(summary.to_string(index=False))
print("=" * 64)

if len(failed):
    print(f"\n{len(failed)} component(s) FAILED — do not run the session on this environment.")
else:
    print(f"\nAll good. {(summary.status == 'SKIP').sum()} skipped, rest passing.")

# In CI this makes the job red.
if len(failed) and os.environ.get("CI"):
    raise SystemExit(1)
