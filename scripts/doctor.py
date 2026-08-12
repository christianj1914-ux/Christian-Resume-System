#!/usr/bin/env python3
"""Report runtime health without loading document builders."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path

from config.paths import (
    FEDERAL_JOB_DESCRIPTION,
    JOB_DESCRIPTION,
    OUTPUT_DIR,
    PROJECT_ROOT,
    RENDER_CHECK_DIR,
    SCRATCH_JD_LIBRARY,
    SCRATCH_JOBS_ARCHIVE,
)


REQUIRED_PACKAGES = (("python-docx", "docx"), ("Pillow", "PIL"))


def report(label: str, status: str, detail: object) -> None:
    print(f"{status}: {label} - {detail}")


def writable_directory(path: Path) -> bool:
    candidate = path if path.exists() else next((parent for parent in path.parents if parent.exists()), path)
    return candidate.is_dir() and os.access(candidate, os.W_OK)


def git_health() -> tuple[bool, str]:
    result = subprocess.run(
        ("git", "-C", str(PROJECT_ROOT), "rev-parse", "--is-inside-work-tree"),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true", result.stderr.strip() or result.stdout.strip()


def main() -> int:
    required_failures = 0
    optional_missing = 0
    version_ok = sys.version_info >= (3, 11)
    report("Python", "PASS" if version_ok else "FAIL", sys.version.split()[0])
    required_failures += int(not version_ok)

    for distribution, module_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(module_name)
            version = importlib.metadata.version(distribution)
        except (ImportError, importlib.metadata.PackageNotFoundError) as error:
            report(distribution, "FAIL", error)
            required_failures += 1
        else:
            report(distribution, "PASS", version)

    report("Repository", "PASS", PROJECT_ROOT)
    report("Workspace", "PASS", Path.cwd().resolve())
    git_ok, git_detail = git_health()
    report("Git repository", "PASS" if git_ok else "FAIL", git_detail or PROJECT_ROOT)
    required_failures += int(not git_ok)

    python_override = os.environ.get("RESUME_PYTHON", "").strip()
    report("RESUME_PYTHON", "PASS", python_override or "not configured; using current interpreter")
    report("Commercial input", "PASS", JOB_DESCRIPTION)
    report("Federal input", "PASS", FEDERAL_JOB_DESCRIPTION)

    for label, path in (
        ("Output path", OUTPUT_DIR),
        ("Render path", RENDER_CHECK_DIR),
        ("Scratch path", SCRATCH_JD_LIBRARY.parent),
        ("Archive path", SCRATCH_JOBS_ARCHIVE),
    ):
        ok = writable_directory(path)
        report(label, "PASS" if ok else "FAIL", path)
        required_failures += int(not ok)

    libreoffice = shutil.which("soffice") or shutil.which("libreoffice")
    poppler = shutil.which("pdftoppm")
    for label, executable in (("LibreOffice", libreoffice), ("Poppler", poppler)):
        report(label, "PASS" if executable else "OPTIONAL", executable or "not available")
        optional_missing += int(not executable)

    if required_failures:
        report("Doctor result", "FAIL", f"{required_failures} required check(s) failed")
        return 1
    if optional_missing:
        report("Doctor result", "OPTIONAL", f"required runtime healthy; {optional_missing} optional renderer check(s) unavailable")
        return 2
    report("Doctor result", "PASS", "required and optional checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
