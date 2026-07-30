"""Parquet cache.

Members read from here almost always. The Actions pipeline writes here nightly.
The cache is just a directory of parquet files, so it behaves the same whether
that directory is a mounted Shared Drive (Phase 1) or a server volume (Phase 2).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from . import config

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def key(symbol: str, source: str) -> str:
    """Turn 'BTC/USDT' into a filename that survives every filesystem."""
    return f"{source}__{_SAFE.sub('-', symbol).strip('-')}"


def path_for(symbol: str, source: str) -> Path:
    return config.resolve().cache_dir / f"{key(symbol, source)}.parquet"


def quality_path_for(symbol: str, source: str) -> Path:
    return config.resolve().quality_dir / f"{key(symbol, source)}.json"


def exists(symbol: str, source: str) -> bool:
    return path_for(symbol, source).exists()


def read(symbol: str, source: str) -> pd.DataFrame:
    df = pd.read_parquet(path_for(symbol, source))
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df.sort_index()


def write(df: pd.DataFrame, symbol: str, source: str) -> Path:
    target = path_for(symbol, source)
    target.parent.mkdir(parents=True, exist_ok=True)
    df.sort_index().to_parquet(target, compression="snappy")
    return target


def read_quality(symbol: str, source: str) -> dict | None:
    p = quality_path_for(symbol, source)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def catalogue() -> pd.DataFrame:
    """Everything currently cached, with its quality verdict."""
    cache_dir = config.resolve().cache_dir
    if not cache_dir.exists():
        return pd.DataFrame(columns=["symbol", "source", "rows", "ok"])

    rows = []
    for f in sorted(cache_dir.glob("*.parquet")):
        source, _, symbol = f.stem.partition("__")
        quality = read_quality(symbol, source) or {}
        rows.append(
            {
                "symbol": symbol,
                "source": source,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "rows": quality.get("rows"),
                "end": quality.get("end"),
                "ok": quality.get("ok"),
                "errors": len(quality.get("issues", []) or []),
            }
        )
    return pd.DataFrame(rows)


def available() -> bool:
    """False when Drive is not mounted, which is the usual cause of confusion."""
    return config.resolve().cache_dir.exists()
