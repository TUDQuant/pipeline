# Changing the data: stocks, crypto, macro

Everything members can load with `data.equities(...)`, `data.crypto(...)` and
`data.macro(...)` is decided by one file:

```
data-pipelines/universe.yml
```

Change that file through a normal pull request ([`contributing.md`](contributing.md)),
and the nightly pipeline does the rest.

---

## How the pipeline uses it

Every night GitHub Actions reads `universe.yml` and, **for every symbol, refetches
its entire history from the `start` date**, validates it, and overwrites the
parquet file in the Shared Drive.

| Group | Runs | Source | History from |
|---|---|---|---|
| `equities` | 23:15 UTC, Mon–Fri | yfinance (Alpha Vantage as fallback) | `start: "2015-01-01"` |
| `macro` | 23:15 UTC, Mon–Fri | FRED | `start: "2000-01-01"` |
| `crypto` | 00:30 UTC, daily | ccxt: Binance → Kraken → Coinbase | ~2 years in practice — see below |

Consequences:

- **A newly added symbol arrives with its full history** on its first run. There
  is no backfill step.
- **Changing `start` changes history for every symbol in that group** on the next
  run, because everything is refetched.
- A symbol that only listed recently (an IPO in 2021, say) simply starts at its
  listing date.

---

## Adding a symbol

### 1. Find the right identifier

The identifier must be exactly what the source expects. A wrong one is the most
common mistake, and the pipeline does not fail on it — it logs `FAIL` for that
one symbol and carries on.

**Stocks, ETFs, indices — Yahoo Finance tickers.** Search on
https://finance.yahoo.com and copy the symbol shown next to the name.

| Kind | Example | Note |
|---|---|---|
| US stock / ETF | `AAPL`, `SPY` | plain |
| German stock (Xetra) | `SAP.DE`, `SIE.DE` | `.DE` suffix |
| Other exchanges | `ASML.AS`, `NESN.SW`, `7203.T` | exchange suffix |
| Index | `^GDAXI`, `^GSPC`, `^STOXX50E` | starts with `^` |
| FX pair | `EURUSD=X` | `=X` suffix |

**Crypto — exchange pairs** in `BASE/QUOTE` form: `BTC/USDT`, `ETH/USDT`. Use
`USDT` as quote; it is listed on all three exchanges in the fallback chain.

**Macro — FRED series IDs.** Search on https://fred.stlouisfed.org; the ID is
the code in the page URL and in brackets after the title, e.g. `DGS10`,
`CPIAUCSL`, `FEDFUNDS`. Daily, monthly and quarterly series all work.

### 2. Test it before you open the PR (stocks and crypto)

In any Colab notebook after the setup cell, or locally in the venv:

```python
from tudquant import data
df = data.fetch_live("SAP.DE", "equities", start="2015-01-01")
df.tail(), len(df), df.index[0]
print(data.check(df, "SAP.DE", "equities"))
```

You want a sensible number of rows, a first date near the start, and no
`ERROR` lines in the check. For crypto use `"crypto"` as the second argument.

Macro cannot be tested this way by members — it needs the club FRED key, which
only lives in the pipeline. Confirm the series exists on the FRED website
instead.

### 3. Edit `universe.yml`

Add the identifier under the right group, with a short comment saying why:

```yaml
equities:
  start: "2015-01-01"
  symbols:
    - AAPL
    ...
    - SAP.DE     # German large cap, for the DAX valuation session
```

Indentation is two spaces and a dash. Tabs break the file.

### 4. PR, merge, and run it now instead of tonight

After the PR is merged ([`contributing.md`](contributing.md)), infrastructure can
trigger the run immediately:

```bash
gh workflow run update-data.yml -f group=equities     # or crypto / macro / all
sleep 10
gh run watch
```

In the log, look for your symbol:

```
== equities ==
  OK    SAP.DE: 2950 rows to 2026-10-12 (0E/1W)
```

`OK` with `0E` (zero errors) is what you want. A few warnings (`W`) are normal —
they flag holidays or large single-day moves for a human to glance at. `FAIL`
means the identifier is wrong or the source refused it; `BAD` means it downloaded
but failed validation (read the quality report before anyone uses it).

### 5. Confirm members can see it

In Colab on a club account:

```python
data.catalogue()             # the new row should be there, ok = True
data.equities("SAP.DE").tail()
```

---

## Removing a symbol

Deleting a line from `universe.yml` **stops the nightly refresh**. It does not
delete the data: the pipeline only ever uploads, never removes. The old file
stays in the Shared Drive, keeps appearing in `data.catalogue()`, and quietly
goes stale — its `end` date stops moving.

So removal is two steps:

1. Remove the line from `universe.yml` via a PR.
2. In the `TUD Quant` Shared Drive, delete the two files for that symbol:
   - `Data/parquet/<group>__<name>.parquet`
   - `Data/quality/<group>__<name>.json`

   Only infrastructure can do this; members have Viewer access. The file name is
   the symbol with characters like `/` and `^` replaced or dropped:

   | Symbol | Files |
   |---|---|
   | `BTC/USDT` | `crypto__BTC-USDT.parquet`, `.json` |
   | `^GDAXI` | `equities__GDAXI.parquet`, `.json` |
   | `SAP.DE` | `equities__SAP.DE.parquet`, `.json` |
   | `DGS10` | `macro__DGS10.parquet`, `.json` |

If a lesson still uses the symbol, leaving the stale file in place can be the
right call — just know that it is no longer updating.

---

## Changing how much history

Edit the group's `start` date in `universe.yml`. The next run refetches every
symbol in that group from the new date. Going further back only helps if the
source has the data: yfinance generally goes back decades for large stocks, FRED
for most series goes back much further than 2000.

### The crypto exception

Crypto history is currently about **two years**, regardless of `start`. Binance
blocks GitHub's servers, so the pipeline falls back to Kraken, and Kraken's
candle endpoint only returns the most recent ~720 days. That is why every crypto
file starts around 2024-08 even though `start` says 2018.

Two further details for whoever fixes this:

- The `exchanges:` list in `universe.yml` is **not read** by the code — the order
  is hard-coded in `tudquant/sources/crypto.py`. Editing it in the YAML changes
  nothing.
- The paging loop in `crypto.py` stops as soon as one request returns fewer than
  1000 candles. Coinbase returns at most 300 per request, so even if Coinbase
  were tried first it would stop after one page.

Getting longer crypto history means fixing the paging and preferring an exchange
that serves deep history to datacenter IPs. Until then, treat crypto as
two-year data in lessons.

---

## Limits — keep the universe small

- **Every symbol is a nightly request**, and yfinance is an unofficial scraper.
  Hundreds of symbols will get the pipeline rate-limited. The current ~20 is
  comfortable; a few dozen is fine.
- **Alpha Vantage, the equity fallback, allows 25 requests per day** on the free
  tier. If yfinance has a bad night, only the first 25 equities can fall back.
- **Daily data only.** Intraday or tick data is not available from these free
  sources at all; that is a budget decision, not a config change.
- **Add on request, remove when a lesson is over.** A symbol nobody uses is a
  nightly request that can fail and a row of noise in the catalogue.
