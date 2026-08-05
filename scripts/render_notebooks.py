#!/usr/bin/env python3
"""Render curriculum/ and notebooks/ .py sources into colab/*.ipynb.

Run this locally before committing whenever you change a .py source:

    python scripts/render_notebooks.py

Why a script and not a bare jupytext loop: nbformat 4.5 gives every cell a
random `id`, so two renders of an unchanged source produce different files.
That makes "is colab/ up to date?" impossible to answer with a diff. We
therefore assign each cell a deterministic id derived from its position and
content, so identical sources always render byte-identical notebooks.

CI runs this same script and fails if the result differs from what is
committed. CI does not generate the notebooks itself: a bot commit would land
on the PR head without triggering a CI run, leaving the required status check
missing and the pull request unmergeable.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ["curriculum", "notebooks"]
OUT_DIR = ROOT / "colab"


def deterministic_id(index: int, source: str) -> str:
    """Stable 8-char id: same position + same content -> same id."""
    digest = hashlib.sha1(f"{index}:{source}".encode()).hexdigest()
    return digest[:8]


def normalise(path: Path) -> None:
    nb = json.loads(path.read_text())
    for i, cell in enumerate(nb.get("cells", [])):
        cell["id"] = deterministic_id(i, "".join(cell.get("source", [])))
    # Trailing newline keeps git happy and matches jupytext's own output.
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    rendered = []

    for directory in SOURCE_DIRS:
        for src in sorted((ROOT / directory).glob("*.py")):
            out = OUT_DIR / f"{src.stem}.ipynb"
            result = subprocess.run(
                ["jupytext", "--to", "notebook", str(src), "-o", str(out)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"jupytext failed on {src}:\n{result.stderr}", file=sys.stderr)
                return 1
            normalise(out)
            rendered.append(out.relative_to(ROOT))

    for path in rendered:
        print(f"rendered {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
