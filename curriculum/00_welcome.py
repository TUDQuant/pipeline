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
# # Welcome to TUD Quant
#
# This is also the template for every club notebook. Copy it, rename it, keep
# the first cell exactly as it is.

# %%
# --- setup: do not change ----------------------------------------------------
# !pip install -q "tudquant[backtest] @ git+https://github.com/tud-quant/quant-club.git@v0.1.0"

import tudquant

tudquant.bootstrap()

# %% [markdown]
# ## What data do we have?

# %%
from tudquant import data

data.catalogue()

# %% [markdown]
# ## Loading a series
#
# This reads from the nightly cache, not from a live API. It is fast, it is the
# same data everyone else has, and it does not burn a shared rate limit.

# %%
aapl = data.equities("AAPL", start="2020-01-01")
aapl.tail()

# %%
aapl["close"].plot(title="AAPL close", figsize=(10, 4))

# %% [markdown]
# ## Checking that the data is trustworthy
#
# Every cached dataset was validated last night. Look at the report before you
# build anything on top of a series — a backtest on a series with an unadjusted
# split will show you a strategy that never existed.

# %%
data.quality("AAPL", "equities")

# %% [markdown]
# ## A first backtest
#
# Ten-day against thirty-day moving average. The point here is not that this is
# a good strategy — it is not — but that the whole path from data to result is
# four lines once the environment does its job.

# %%
import vectorbt as vbt

price = aapl["close"]
fast, slow = price.rolling(10).mean(), price.rolling(30).mean()

portfolio = vbt.Portfolio.from_signals(
    price, entries=fast > slow, exits=fast < slow, init_cash=10_000, fees=0.001
)
portfolio.stats()

# %% [markdown]
# ## Your turn
#
# 1. Pick a different symbol from `data.catalogue()`.
# 2. Change the two moving average windows.
# 3. Compare against simply holding the asset — `portfolio.total_return()` versus
#    `price.iloc[-1] / price.iloc[0] - 1`.
#
# Then ask yourself why the comparison in (3) is still not an honest one. That
# question is most of the next session.
#
# ---
#
# **Saving your work:** File → Save a copy in Drive keeps it in your own folder.
# To contribute it back, convert to `.py` first — see `docs/notebooks.md`.
