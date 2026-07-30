import numpy as np
import pandas as pd
import pytest

from tudquant import cache


@pytest.fixture(autouse=True)
def data_root(tmp_path, monkeypatch):
    monkeypatch.setenv("TUDQUANT_DATA_ROOT", str(tmp_path))
    return tmp_path


def frame(n=10):
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({"close": np.arange(n, dtype=float)}, index=idx)


def test_roundtrip():
    cache.write(frame(), "AAPL", "equities")
    out = cache.read("AAPL", "equities")
    assert len(out) == 10
    assert isinstance(out.index, pd.DatetimeIndex)


def test_symbols_with_slashes_are_safe():
    cache.write(frame(), "BTC/USDT", "crypto")
    assert cache.exists("BTC/USDT", "crypto")
    assert "/" not in cache.path_for("BTC/USDT", "crypto").name


def test_catalogue_lists_written_datasets():
    cache.write(frame(), "AAPL", "equities")
    cache.write(frame(), "ETH/USDT", "crypto")
    cat = cache.catalogue()
    assert len(cat) == 2
    assert set(cat["source"]) == {"equities", "crypto"}


def test_catalogue_empty_when_nothing_cached():
    assert cache.catalogue().empty
