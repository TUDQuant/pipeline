"""Macro series from FRED.

FRED series are single-column and irregular by nature (monthly, quarterly,
weekly), so gap checking uses the 'none' calendar rather than business days.
"""

from __future__ import annotations

import pandas as pd

from .. import config

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch(series_id: str, start: str = "2000-01-01") -> pd.DataFrame:
    import requests

    key = config.api_key("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY is not set - this runs in the pipeline, not in notebooks")

    response = requests.get(
        BASE_URL,
        params={
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "observation_start": start,
        },
        timeout=30,
    )
    response.raise_for_status()
    observations = response.json().get("observations", [])
    if not observations:
        raise RuntimeError(f"FRED returned no observations for {series_id}")

    df = pd.DataFrame(observations)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    # FRED encodes missing values as "."
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.set_index("date").sort_index().rename(columns={"value": series_id.lower()})
