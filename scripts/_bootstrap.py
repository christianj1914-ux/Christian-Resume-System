"""Ensure local imports resolve and runtime bytecode stays fresh."""

from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
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
    """Route pyc writes to a temporary process-owned cache directory."""

    existing_env = os.environ.get("PYTHONPYCACHEPREFIX", "").strip()
    managed_owner = os.environ.get("RESUME_MANAGED_PYCACHE_OWNER_PID", "").strip()
    if existing_env and not managed_owner:
        prefix = Path(existing_env)
        prefix.mkdir(parents=True, exist_ok=True)
        sys.pycache_prefix = str(prefix)
        return prefix
    if existing_env and managed_owner == str(os.getpid()):
        return Path(existing_env)

    prefix = Path(tempfile.mkdtemp(prefix=f"resume-system-pycache-{os.getpid()}-"))
    os.environ["PYTHONPYCACHEPREFIX"] = str(prefix)
    os.environ["RESUME_MANAGED_PYCACHE_OWNER_PID"] = str(os.getpid())
    sys.pycache_prefix = str(prefix)
    atexit.register(shutil.rmtree, prefix, True)
    return prefix
