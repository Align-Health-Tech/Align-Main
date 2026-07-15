"""Versioned smoke result paths — never overwrite prior runs."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def next_result_path(results_dir: Path, *, prefix: str = "results") -> Path:
    """Return ``results_dir/vNNN_{prefix}_YYYY-MM-DD_HHMMSS.txt`` (new file)."""
    results_dir.mkdir(parents=True, exist_ok=True)
    version = _next_version(results_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return results_dir / f"v{version:03d}_{prefix}_{stamp}.txt"


def _next_version(results_dir: Path) -> int:
    pattern = re.compile(r"^v(\d+)_")
    highest = 0
    for path in results_dir.iterdir():
        if not path.is_file():
            continue
        match = pattern.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1
