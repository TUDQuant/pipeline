"""The one interface members use.

    from tudquant import data

    px  = data.equities("AAPL")
    btc = data.crypto("BTC/USDT")
    y10 = data.macro("DGS10")

Resolution order is cache first, live second. On free-tier Colab the cache is
effectively the only path: fifteen to thirty members each pulling the same
symbols would exhaust the free API tiers before the session ended, which is why
the nightly pipeline exists.

Nothing in this module knows about Colab or Drive. That is what makes the move
to JupyterHub a configuration change instead of a rewrite.
"""

from __future__ import annotations

import warnings

import pandas as pd

from . import cache, config, validation
from .sources import crypto as _crypto
from .sources import equities as _equities
from .sources import macro as _macro

CALENDARS = {"equities": "business", "crypto": "daily", "macro": "none"}


class DataUnavailable(RuntimeError):
    """Raised when neither the cache nor a live source can serve a request."""


def equities(symbol: str, start: str | None = None, end: str | None = None,
             live: bool = False, quiet: bool = False) -> pd.DataFrame:
    return _get(symbol, "equities", start, end, live, quiet)


def crypto(symbol: str, start: str | None = None, end: str | None = None,
           live: bool = False, quiet: bool = False) -> pd.DataFrame:
    return _get(symbol, "crypto", start, end, live, quiet)


def macro(series_id: str, start: str | None = None, end: str | None = None,
          live: bool = False, quiet: bool = False) -> pd.DataFrame:
    return _get(series_id, "macro", start, end, live, quiet)


def _get(symbol: str, source: str, start, end, live: bool, quiet: bool) -> pd.DataFrame:
    if not live and cache.exists(symbol, source):
        df = cache.read(symbol, source)
        if not quiet:
            _warn_if_bad(symbol, source)
        return _slice(df, start, end)

    if not live and not cache.available():
        raise DataUnavailable(
            f"No cached data for {symbol} and the data directory is not reachable "
            f"({config.resolve().data_root}).\n"
            "In Colab this almost always means Drive is not mounted - "
            "run tudquant.bootstrap() again and approve the Drive prompt."
        )

    df = fetch_live(symbol, source, start)
    return _slice(df, start, end)


def fetch_live(symbol: str, source: str, start: str | None = None) -> pd.DataFrame:
    """Go to the API. Used by the pipeline; members rarely need this."""
    if source == "equities":
        return _equities.fetch(symbol, start=start or "2015-01-01")
    if source == "crypto":
        return _crypto.fetch(symbol, start=start or "2018-01-01")
    if source == "macro":
        return _macro.fetch(symbol, start=start or "2000-01-01")
    raise ValueError(f"unknown source {source!r}")


def _slice(df: pd.DataFrame, start, end) -> pd.DataFrame:
    if start is not None:
        df = df.loc[str(start):]
    if end is not None:
        df = df.loc[:str(end)]
    return df


def _warn_if_bad(symbol: str, source: str) -> None:
    quality = cache.read_quality(symbol, source)
    if quality is None or quality.get("ok", True):
        return
    problems = [i["message"] for i in quality.get("issues", []) if i["severity"] == "error"]
    warnings.warn(
        f"\n{symbol} failed data quality checks. Do not trust a backtest on this "
        f"series until it is fixed:\n  - " + "\n  - ".join(problems) +
        f"\nFull report: tudquant.data.quality({symbol!r}, {source!r})",
        stacklevel=3,
    )


def quality(symbol: str, source: str) -> validation.QualityReport | None:
    """The stored report for a cached dataset."""
    payload = cache.read_quality(symbol, source)
    if payload is None:
        return None
    issues = [validation.Issue(**i) for i in payload.pop("issues", [])]
    payload.pop("ok", None)
    return validation.QualityReport(issues=issues, **payload)


def check(df: pd.DataFrame, symbol: str = "<in-memory>", source: str = "equities"):
    """Validate a DataFrame you built yourself, before you backtest it."""
    return validation.validate(df, symbol, source, CALENDARS.get(source, "business"))


def catalogue() -> pd.DataFrame:
    """Everything the club has cached right now."""
    return cache.catalogue()
