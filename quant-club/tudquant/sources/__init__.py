"""Data source adapters.

Each adapter returns a DataFrame with a DatetimeIndex named 'date' and, for
price data, lowercase columns: open, high, low, close, volume (+ adj_close
where the source provides one).

Adapters are only called by the nightly pipeline. Members read the cache.
"""

from . import crypto, equities, macro

__all__ = ["crypto", "equities", "macro"]
