import numpy as np
import pandas as pd
import pytest

from tudquant import validation


def series(n=60, start="2024-01-01", freq="B"):
    idx = pd.date_range(start, periods=n, freq=freq)
    px = pd.Series(np.linspace(100, 120, n), index=idx)
    return pd.DataFrame(
        {"open": px, "high": px * 1.01, "low": px * 0.99, "close": px, "volume": 1e6}
    )


def test_clean_series_passes():
    report = validation.validate(series(), "CLEAN", "equities")
    assert report.ok
    assert report.issues == []


def test_empty_series_is_an_error():
    report = validation.validate(pd.DataFrame(), "EMPTY", "equities")
    assert not report.ok


def test_unadjusted_split_is_an_error():
    df = series()
    df.loc[df.index[30]:, ["open", "high", "low", "close"]] /= 2
    report = validation.validate(df, "SPLIT", "equities")
    assert not report.ok
    assert any(i.check == "split" for i in report.errors)


def test_long_gap_is_an_error():
    df = series(n=120)
    df = df.drop(df.index[40:70])
    report = validation.validate(df, "GAPPY", "equities")
    assert any(i.check == "gaps" for i in report.errors)


def test_ohlc_inconsistency_detected():
    df = series()
    df.loc[df.index[5], "high"] = 0.5 * df.loc[df.index[5], "low"]
    report = validation.validate(df, "BADOHLC", "equities")
    assert any(i.check == "ohlc" for i in report.errors)


def test_stale_prices_warn():
    df = series()
    df.loc[df.index[10:20], "close"] = df["close"].iloc[10]
    report = validation.validate(df, "STALE", "equities")
    assert any(i.check == "stale" for i in report.warnings)


def test_duplicate_index_is_an_error():
    df = series()
    df = pd.concat([df, df.iloc[[3]]]).sort_index()
    report = validation.validate(df, "DUPE", "equities")
    assert any(i.check == "index" for i in report.errors)


def test_report_roundtrips_to_json(tmp_path):
    report = validation.validate(series(), "RT", "equities")
    path = tmp_path / "rt.json"
    report.save(path)
    assert path.exists()
    assert '"ok": true' in path.read_text()


@pytest.mark.parametrize("calendar", ["business", "daily", "none"])
def test_calendars_do_not_crash(calendar):
    validation.validate(series(), "CAL", "equities", calendar)


def test_macro_monthly_series_is_not_gap_checked():
    """Regression: FRED monthly series were flagged as 97% missing because the
    'none' calendar fell through to a daily comparison."""
    idx = pd.date_range("2000-01-01", periods=318, freq="MS")
    df = pd.DataFrame({"cpiaucsl": np.linspace(170, 320, 318)}, index=idx)
    report = validation.validate(df, "CPIAUCSL", "macro", calendar="none")
    assert report.ok
    assert not any(i.check == "gaps" for i in report.issues)


def test_macro_business_daily_series_is_not_gap_checked():
    idx = pd.bdate_range("2000-01-01", periods=6932)
    df = pd.DataFrame({"dgs10": np.linspace(1, 5, 6932)}, index=idx)
    report = validation.validate(df, "DGS10", "macro", calendar="none")
    assert report.ok
