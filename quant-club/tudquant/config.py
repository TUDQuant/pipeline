"""Runtime configuration.

This module is the ONLY place that knows where data lives. Phase 1 (Colab +
Shared Drive) and Phase 2 (JupyterHub on a VM) differ by one environment
variable and nothing else. Do not hardcode paths anywhere else in the package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Phase 1 default. Change the Shared Drive name here if the club renames it.
COLAB_DATA_ROOT = "/content/drive/Shareddrives/TUD Quant/data"

# Phase 2 default, used automatically once we are on JupyterHub.
SERVER_DATA_ROOT = "/srv/tudquant/data"

# Local fallback for laptops and CI.
LOCAL_DATA_ROOT = "~/.tudquant/data"

ENV_DATA_ROOT = "TUDQUANT_DATA_ROOT"


def in_colab() -> bool:
    try:
        import google.colab  # noqa: F401

        return True
    except ImportError:
        return False


def in_ci() -> bool:
    return os.environ.get("CI", "").lower() == "true"


@dataclass(frozen=True)
class Config:
    data_root: Path
    environment: str

    @property
    def cache_dir(self) -> Path:
        return self.data_root / "parquet"

    @property
    def quality_dir(self) -> Path:
        return self.data_root / "quality"


def resolve() -> Config:
    """Work out where data lives, in priority order."""
    explicit = os.environ.get(ENV_DATA_ROOT)
    if explicit:
        return Config(Path(explicit).expanduser(), "explicit")

    if in_colab():
        return Config(Path(COLAB_DATA_ROOT), "colab")

    server = Path(SERVER_DATA_ROOT)
    if server.exists():
        return Config(server, "server")

    return Config(Path(LOCAL_DATA_ROOT).expanduser(), "local")


def api_key(name: str) -> str | None:
    """Fetch an API key.

    Members never hold club keys. In Colab this reads a userdata secret if the
    member happens to have one; in Actions it reads the repository secret.
    Returning None is normal and callers must degrade to cached data.
    """
    value = os.environ.get(name)
    if value:
        return value

    if in_colab():
        try:
            from google.colab import userdata

            return userdata.get(name)
        except Exception:
            return None
    return None
