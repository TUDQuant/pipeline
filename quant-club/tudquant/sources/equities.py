"""Equity daily bars: yfinance first, Alpha Vantage as the fallback.

yfinance has no key and no documented rate limit but is an unofficial scraper
and does break. Alpha Vantage is a documented API but the free tier is tight
(25 requests/day at time of writing), which is exactly why it lives in the
nightly pipeline and never in a member notebook.
"""

from __future__ import annotations

import pandas as pd

from .. import config

COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


def fetch(symbol: str, start: str = "2015-01-01", end: str | None = None) -> pd.DataFrame:
    try:
        return _from_yfinance(symbol, start, end)
    except Exception as exc:  # noqa: BLE001 - fallback is the whole point
        key = config.api_key("ALPHAVANTAGE_API_KEY")
        if not key:
            raise RuntimeError(
                f"yfinance failed for {symbol} ({exc}) and no Alpha Vantage key is set"
            ) from exc
        return _from_alpha_vantage(symbol, key, start, end)


def _from_yfinance(symbol: str, start: str, end: str | None) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(
        symbol,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"yfinance returned nothing for {symbol}")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    raw = raw.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    raw.index.name = "date"
    return raw[[c for c in COLUMNS if c in raw.columns]]


def _from_alpha_vantage(symbol: str, key: str, start: str, end: str | None) -> pd.DataFrame:
    import requests

    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": "full",
            "apikey": key,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    series = payload.get("Time Series (Daily)")
    if not series:
        note = payload.get("Note") or payload.get("Information") or payload.get("Error Message")
        raise RuntimeError(f"Alpha Vantage returned no data for {symbol}: {note}")

    df = pd.DataFrame(series).T
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df = df.rename(
        columns={
            "1. open": "open",
            "2. high": "high",
            "3. low": "low",
            "4. close": "close",
            "5. adjusted close": "adj_close",
            "6. volume": "volume",
        }
    )
    df = df[[c for c in COLUMNS if c in df.columns]].astype(float).sort_index()
    return df.loc[start:end] if end else df.loc[start:]
