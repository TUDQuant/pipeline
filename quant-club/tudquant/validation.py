"""Data quality checks.

Marven's point, and it is the right one: a member who backtests on silently
broken data draws a confident wrong conclusion and learns something false.
Every dataset that enters the club therefore carries a quality report, and the
report is visible by default rather than buried in a log.

Checks are deliberately simple and readable. A member should be able to open
this file and understand exactly what was and was not verified.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

# A single-day move larger than this in an unadjusted series is more likely a
# corporate action than a real return, and is worth surfacing.
SPLIT_SUSPICION_RETURN = 0.35

# Common split ratios, used to recognise a suspicious jump as a likely split.
COMMON_SPLITS = [2, 3, 4, 5, 7, 10, 20]

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Issue:
    severity: str  # "error" | "warning" | "info"
    check: str
    message: str
    detail: dict = field(default_factory=dict)


@dataclass
class QualityReport:
    symbol: str
    source: str
    rows: int
    start: str | None
    end: str | None
    issues: list = field(default_factory=list)

    @property
    def errors(self) -> list:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["ok"] = self.ok
        return payload

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    def __str__(self) -> str:
        head = f"{self.symbol} [{self.source}] {self.rows} rows {self.start} to {self.end}"
        if not self.issues:
            return head + "\n  no issues found"
        lines = [head]
        for issue in sorted(self.issues, key=lambda i: SEVERITY_ORDER[i.severity]):
            lines.append(f"  {issue.severity.upper():<8} {issue.check}: {issue.message}")
        return "\n".join(lines)

    def _repr_html_(self) -> str:
        colour = "#c0392b" if self.errors else ("#d68910" if self.warnings else "#1e8449")
        verdict = "FAILED" if self.errors else ("PASSED WITH WARNINGS" if self.warnings else "PASSED")
        rows = "".join(
            f"<tr><td style='padding:2px 10px'>{i.severity}</td>"
            f"<td style='padding:2px 10px'>{i.check}</td>"
            f"<td style='padding:2px 10px'>{i.message}</td></tr>"
            for i in sorted(self.issues, key=lambda i: SEVERITY_ORDER[i.severity])
        )
        return (
            f"<div style='font-family:monospace'>"
            f"<b>{self.symbol}</b> <span style='color:{colour}'>{verdict}</span><br>"
            f"{self.source} &middot; {self.rows} rows &middot; {self.start} to {self.end}"
            f"<table>{rows}</table></div>"
        )


def _ohlc_columns(df: pd.DataFrame) -> bool:
    return {"open", "high", "low", "close"}.issubset(df.columns)


def validate(df: pd.DataFrame, symbol: str, source: str, calendar: str = "business") -> QualityReport:
    """Run every check and return a report. Never raises on bad data."""
    report = QualityReport(
        symbol=symbol,
        source=source,
        rows=len(df),
        start=str(df.index.min().date()) if len(df) else None,
        end=str(df.index.max().date()) if len(df) else None,
    )

    if df.empty:
        report.issues.append(Issue("error", "empty", "dataset has no rows"))
        return report

    _check_index(df, report)
    _check_prices(df, report)
    _check_gaps(df, report, calendar)
    _check_splits(df, report)
    _check_stale(df, report)
    return report


def _check_index(df: pd.DataFrame, report: QualityReport) -> None:
    if not isinstance(df.index, pd.DatetimeIndex):
        report.issues.append(Issue("error", "index", "index is not a DatetimeIndex"))
        return
    dupes = int(df.index.duplicated().sum())
    if dupes:
        report.issues.append(
            Issue("error", "index", f"{dupes} duplicated timestamps", {"count": dupes})
        )
    if not df.index.is_monotonic_increasing:
        report.issues.append(Issue("error", "index", "index is not sorted ascending"))


def _check_prices(df: pd.DataFrame, report: QualityReport) -> None:
    if not _ohlc_columns(df):
        return

    non_positive = int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    if non_positive:
        report.issues.append(
            Issue("error", "prices", f"{non_positive} rows with non-positive prices",
                  {"count": non_positive})
        )

    inconsistent = int(
        (
            (df["high"] < df["low"])
            | (df["high"] < df["open"])
            | (df["high"] < df["close"])
            | (df["low"] > df["open"])
            | (df["low"] > df["close"])
        ).sum()
    )
    if inconsistent:
        report.issues.append(
            Issue("error", "ohlc", f"{inconsistent} rows violate low <= open/close <= high",
                  {"count": inconsistent})
        )

    nulls = int(df[["open", "high", "low", "close"]].isna().any(axis=1).sum())
    if nulls:
        report.issues.append(
            Issue("warning", "missing", f"{nulls} rows with missing OHLC values", {"count": nulls})
        )


def _check_gaps(df: pd.DataFrame, report: QualityReport, calendar: str) -> None:
    """Flag missing sessions.

    'business' approximates an equity calendar and will show a handful of false
    positives on public holidays. That is the intended trade-off: we would
    rather a member sees a holiday flagged than misses a month of missing data.
    'daily' is used for crypto, which trades every day.
    """
    if not isinstance(df.index, pd.DatetimeIndex) or len(df) < 2:
        return

    freq = "B" if calendar == "business" else "D"
    expected = pd.date_range(df.index.min(), df.index.max(), freq=freq)
    missing = expected.difference(df.index.normalize())

    if len(missing) == 0:
        return

    gaps = _consecutive_runs(missing)
    longest = max(len(g) for g in gaps)
    pct = len(missing) / max(len(expected), 1)

    severity = "error" if longest >= 10 or pct > 0.10 else "warning"
    report.issues.append(
        Issue(
            severity,
            "gaps",
            f"{len(missing)} expected sessions missing ({pct:.1%}), longest run {longest} days",
            {
                "missing": len(missing),
                "longest_run": longest,
                "first_gap_start": str(gaps[0][0].date()),
            },
        )
    )


def _consecutive_runs(index: pd.DatetimeIndex) -> list:
    runs, current = [], [index[0]]
    for previous, nxt in zip(index[:-1], index[1:], strict=False):
        if (nxt - previous).days <= 3:
            current.append(nxt)
        else:
            runs.append(current)
            current = [nxt]
    runs.append(current)
    return runs


def _check_splits(df: pd.DataFrame, report: QualityReport) -> None:
    """Detect corporate actions that look unhandled.

    If the series is properly split-adjusted there should be no unexplained
    jumps near a common split ratio. If we also have an adjusted close, we
    check that the two series disagree in the way a real adjustment would.
    """
    if "close" not in df.columns or len(df) < 3:
        return

    returns = df["close"].pct_change()
    suspicious = returns[returns.abs() > SPLIT_SUSPICION_RETURN].dropna()

    for date, ret in suspicious.items():
        ratio = 1 / (1 + ret) if ret < 0 else (1 + ret)
        nearest = min(COMMON_SPLITS, key=lambda s: abs(s - ratio))
        looks_like_split = abs(nearest - ratio) / nearest < 0.05

        if looks_like_split:
            report.issues.append(
                Issue(
                    "error",
                    "split",
                    f"{date.date()}: {ret:+.1%} move matches an unadjusted "
                    f"{nearest}:1 split - do not backtest this series",
                    {"date": str(date.date()), "ratio": nearest},
                )
            )
        else:
            report.issues.append(
                Issue(
                    "warning",
                    "jump",
                    f"{date.date()}: {ret:+.1%} single-day move, verify it is real",
                    {"date": str(date.date())},
                )
            )

    if "adj_close" in df.columns:
        factor = (df["adj_close"] / df["close"]).dropna()
        if len(factor) and not factor.is_monotonic_increasing:
            drops = int((factor.diff() < -1e-9).sum())
            if drops > len(factor) * 0.01:
                report.issues.append(
                    Issue(
                        "warning",
                        "adjustment",
                        f"adjustment factor moves erratically ({drops} reversals)",
                        {"reversals": drops},
                    )
                )


def _check_stale(df: pd.DataFrame, report: QualityReport, threshold: int = 5) -> None:
    """Identical closes for many days usually means a dead feed, not a quiet market."""
    if "close" not in df.columns or len(df) < threshold:
        return
    same = df["close"].diff().eq(0)
    runs = (same != same.shift()).cumsum()[same]
    if runs.empty:
        return
    longest = int(runs.value_counts().max())
    if longest >= threshold:
        report.issues.append(
            Issue(
                "warning",
                "stale",
                f"{longest} consecutive days with an unchanged close",
                {"longest_run": longest},
            )
        )


def summarise(reports: list) -> pd.DataFrame:
    """One row per dataset, for the pipeline's daily quality dashboard."""
    return pd.DataFrame(
        [
            {
                "symbol": r.symbol,
                "source": r.source,
                "rows": r.rows,
                "start": r.start,
                "end": r.end,
                "errors": len(r.errors),
                "warnings": len(r.warnings),
                "ok": r.ok,
            }
            for r in reports
        ]
    )
