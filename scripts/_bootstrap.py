"""Ensure the scripts package root is on sys.path for config imports."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent


def ensure_script_path() -> None:
    script_dir = str(_SCRIPT_DIR)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
