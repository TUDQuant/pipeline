"""Crypto daily bars via ccxt.

Binance blocks a lot of datacenter IP ranges, and GitHub Actions runners sit in
exactly those ranges. The exchange is therefore configurable and the pipeline
falls back automatically rather than failing the nightly run.
"""

from __future__ import annotations

import time

import pandas as pd

DEFAULT_EXCHANGES = ["binance", "kraken", "coinbase"]
MAX_BARS_PER_CALL = 1000


def fetch(
    symbol: str,
    start: str = "2018-01-01",
    exchanges: list | None = None,
    timeframe: str = "1d",
) -> pd.DataFrame:
    import ccxt

    errors = []
    for name in exchanges or DEFAULT_EXCHANGES:
        try:
            exchange = getattr(ccxt, name)({"enableRateLimit": True})
            return _fetch_all(exchange, symbol, start, timeframe)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
    raise RuntimeError(f"no exchange returned {symbol}. Tried -> " + " | ".join(errors))


def _fetch_all(exchange, symbol: str, start: str, timeframe: str) -> pd.DataFrame:
    since = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    rows: list = []

    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=MAX_BARS_PER_CALL)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < MAX_BARS_PER_CALL:
            break
        since = batch[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000)

    if not rows:
        raise RuntimeError(f"{exchange.id} returned no candles for {symbol}")

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms")
    df = df.drop(columns="ts").set_index("date").sort_index()
    return df[~df.index.duplicated(keep="last")]
