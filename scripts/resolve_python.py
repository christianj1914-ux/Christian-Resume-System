#!/usr/bin/env python3
"""Print a usable Python executable path for batch wrappers."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_windowsapps_stub(path: Path) -> bool:
    return "windowsapps" in str(path).lower()


def candidate_paths(project_root: Path | None = None) -> list[Path]:
    root = (project_root or Path(__file__).resolve().parents[1]).resolve()
    candidates: list[Path] = []
    env_override = os.environ.get("RESUME_PYTHON", "").strip()
    if env_override:
        candidates.append(Path(env_override))

    candidates.append(root / "venv" / "Scripts" / "python.exe")
    candidates.append(root / "venv" / "bin" / "python")
    candidates.append(Path(sys.executable))

    return candidates


def resolve_python(project_root: Path | None = None) -> Path | None:
    for candidate in candidate_paths(project_root):
        if candidate.is_file() and not is_windowsapps_stub(candidate):
            return candidate
    return None


def main() -> int:
    resolved = resolve_python()
    if resolved is None:
        print(
            "ERROR: No usable Python executable found. Set RESUME_PYTHON or install Python 3.11+.",
            file=sys.stderr,
        )
        return 1
    print(resolved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
