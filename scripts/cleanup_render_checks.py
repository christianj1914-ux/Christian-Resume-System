#!/usr/bin/env python3
"""Delete old disposable DOCX render-check folders.

This script targets disposable render folders only:
- root-level directories named render_check_* from older manual checks
- timestamped subfolders inside the permanent render_check folder

It never deletes the permanent render_check folder itself, source, output, jobs,
scripts, backups, or any folder outside the project root.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import sys
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RENDER_ROOT = PROJECT_ROOT / "render_check"
DEFAULT_HOURS = 24
TIMESTAMPED_RENDER_FOLDER_RE = re.compile(r".+_\d{8}_\d{6}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean old render_check* folders from the resume system root."
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=DEFAULT_HOURS,
        help="Delete render folders older than this many hours. Default: 24.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete matching folders. Without this flag, only preview the cleanup.",
    )
    return parser.parse_args()


def is_safe_render_folder(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
        root = PROJECT_ROOT.resolve(strict=True)
        render_root = RENDER_ROOT.resolve(strict=False)
    except FileNotFoundError:
        return False

    is_old_root_render = (
        resolved.parent == root
        and resolved.is_dir()
        and resolved.name.startswith("render_check_")
    )
    is_nested_render = (
        resolved.parent == render_root
        and resolved.is_dir()
        and resolved.name not in {".", ".."}
    )
    return is_old_root_render or is_nested_render


def is_timestamped_render_subfolder(path: Path) -> bool:
    return path.is_dir() and bool(TIMESTAMPED_RENDER_FOLDER_RE.fullmatch(path.name))


def old_render_folders(hours: float) -> list[Path]:
    cutoff = datetime.now() - timedelta(hours=hours)
    matches: list[Path] = []
    candidates = list(PROJECT_ROOT.glob("render_check_*"))
    if RENDER_ROOT.is_dir():
        candidates.extend(path for path in RENDER_ROOT.iterdir() if is_timestamped_render_subfolder(path))

    for folder in candidates:
        if not is_safe_render_folder(folder):
            continue
        modified = datetime.fromtimestamp(folder.stat().st_mtime)
        if modified < cutoff or not any(folder.iterdir()):
            matches.append(folder)
    return sorted(matches, key=lambda item: item.stat().st_mtime)


def remove_tree(folder: Path) -> list[str]:
    errors: list[str] = []

    def handle_remove_error(function, path, exc_info) -> None:  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            function(path)
        except Exception as error:  # noqa: BLE001
            errors.append(f"{path}: {error}")

    if sys.version_info >= (3, 12):
        shutil.rmtree(folder, onexc=handle_remove_error)
    else:
        shutil.rmtree(folder, onerror=handle_remove_error)
    return errors


def main() -> None:
    args = parse_args()
    if args.hours <= 0:
        raise SystemExit("ERROR: --hours must be greater than 0.")

    folders = old_render_folders(args.hours)
    action = "Deleting" if args.delete else "Would delete"
    errors: list[str] = []
    print(f"{action} {len(folders)} render_check folder(s) older than {args.hours:g} hours or empty:")

    for folder in folders:
        modified = datetime.fromtimestamp(folder.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {folder.name}  modified {modified}")
        if args.delete:
            errors.extend(remove_tree(folder))

    if not args.delete:
        print("\nPreview only. Re-run with --delete to remove these folders.")
    elif errors:
        print("\nSome folders could not be removed:")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
