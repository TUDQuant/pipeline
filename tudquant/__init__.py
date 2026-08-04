"""TUD Quant club library.

Members run exactly this, once, at the top of every notebook:

    !pip install -q "tudquant @ git+https://github.com/tud-quant/quant-club.git@v0.1.0"
    import tudquant; tudquant.bootstrap()

Everything after that is identical on Colab today and on JupyterHub later.
"""

from __future__ import annotations

import sys

from . import config

__version__ = "0.1.0"

# Versions we know work together. Colab silently upgrades its preinstalled
# packages, and vectorbt's numba dependency is the usual casualty, so we check
# rather than hope.
REQUIRED = {
    "numpy": ("1.23", "3.0"),
    "pandas": ("2.0", "3.0"),
}

_BANNER = "TUD Quant {version} | {env} | data: {root}"


def bootstrap(mount_drive: bool = True, verbose: bool = True) -> config.Config:
    """Prepare the session. Safe to call more than once."""

    if config.in_colab() and mount_drive:
        _mount_drive(verbose)

    cfg = config.resolve()

    if verbose:
        print(_BANNER.format(version=__version__, env=cfg.environment, root=cfg.data_root))
        _report_cache(cfg)
        _check_versions()

    return cfg


def _mount_drive(verbose: bool) -> None:
    from pathlib import Path

    if Path("/content/drive/MyDrive").exists():
        return
    from google.colab import drive

    drive.mount("/content/drive")
    if verbose:
        print("Drive mounted.")


def _report_cache(cfg) -> None:
    from . import cache

    if not cache.available():
        print(
            "  ! data directory not found. If you are in Colab, check that the "
            "'TUD Quant' Shared Drive is added to your Drive (Shared drives -> "
            "right click -> Add shortcut)."
        )
        return
    n = len(list(cfg.cache_dir.glob("*.parquet")))
    print(f"  {n} cached datasets available. tudquant.data.catalogue() to list them.")


def _check_versions() -> None:
    """Warn loudly before a lecture instead of failing mysteriously during one."""
    from importlib.metadata import PackageNotFoundError, version

    problems = []
    for package, (low, high) in REQUIRED.items():
        try:
            found = version(package)
        except PackageNotFoundError:
            problems.append(f"{package} is not installed")
            continue
        major_minor = tuple(int(p) for p in found.split(".")[:2])
        if not _in_range(major_minor, low, high):
            problems.append(f"{package} {found} (expected >={low},<{high})")

    if problems:
        print(
            "  ! dependency mismatch: "
            + "; ".join(problems)
            + "\n    Runtime -> Restart session, then re-run this cell. "
            "If it persists, open an issue - do not work around it."
        )


def _in_range(found: tuple, low: str, high: str) -> bool:
    lo = tuple(int(p) for p in low.split("."))
    hi = tuple(int(p) for p in high.split("."))
    return lo <= found < hi


def hello() -> None:
    print(f"tudquant {__version__} on Python {sys.version.split()[0]}")


from . import data  # noqa: E402  (re-exported for `from tudquant import data`)

__all__ = ["bootstrap", "data", "hello", "__version__"]
