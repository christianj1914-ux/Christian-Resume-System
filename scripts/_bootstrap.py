"""Ensure local imports resolve and runtime bytecode stays fresh."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
MINIMUM_PYTHON_VERSION = (3, 11)


def ensure_supported_python_version(version_info: tuple[int, int] | None = None) -> None:
    """Fail early with the repository's declared runtime requirement."""
    detected = version_info or sys.version_info[:2]
    if tuple(detected[:2]) < MINIMUM_PYTHON_VERSION:
        required = ".".join(str(value) for value in MINIMUM_PYTHON_VERSION)
        found = ".".join(str(value) for value in detected[:2])
        raise SystemExit(f"Python {required}+ is required; found Python {found}.")


ensure_supported_python_version()


def ensure_script_path() -> None:
    script_dir = str(_SCRIPT_DIR)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)


def configure_fresh_pycache(project_root: Path | None = None) -> Path:
    """Route pyc writes to a fresh per-run cache directory."""

    existing_env = os.environ.get("PYTHONPYCACHEPREFIX", "").strip()
    existing_runtime = getattr(sys, "pycache_prefix", None)
    if existing_env and existing_runtime and Path(existing_env) == Path(str(existing_runtime)):
        prefix = Path(existing_env)
        prefix.mkdir(parents=True, exist_ok=True)
        return prefix

    root = (project_root or _PROJECT_ROOT).resolve()
    prefix = root / "scratch" / "pycache" / f"session-{os.getpid()}-{uuid.uuid4().hex}"
    prefix.mkdir(parents=True, exist_ok=True)
    os.environ["PYTHONPYCACHEPREFIX"] = str(prefix)
    sys.pycache_prefix = str(prefix)
    return prefix
