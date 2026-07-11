#!/usr/bin/env python3
"""Create, list, and restore full project snapshots."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = PROJECT_ROOT / "backups"

DIRECTORY_ITEMS = (
    "source",
    "jobs",
    "scripts",
    "scratch",
    "output",
)
FILE_ITEMS = (
    "AGENTS.md",
    "CLAUDE.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "tasks.py",
    "run_resume.bat",
    "run_detailed_interview_guide.bat",
    "run_post_interview_debrief.bat",
)
EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create, list, or restore project backups.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("create", help="Create a timestamped backup snapshot.")
    subparsers.add_parser("list", help="List available backup snapshots.")
    restore = subparsers.add_parser("restore", help="Restore a backup snapshot by timestamp.")
    restore.add_argument("timestamp", help="Backup timestamp folder to restore, such as 20260527_093000.")
    restore.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")

    args = parser.parse_args()
    if not args.command:
        args.command = "create"
    return args


def ignore_patterns(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in EXCLUDED_DIR_NAMES}
    ignored.update(name for name in names if name.startswith("render_check"))
    return ignored


def copy_item(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    if source.is_dir():
        shutil.copytree(source, destination, ignore=ignore_patterns)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return True


def create_backup() -> Path:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / timestamp
    backup_dir.mkdir(exist_ok=False)

    copied: list[str] = []
    for name in DIRECTORY_ITEMS:
        if copy_item(PROJECT_ROOT / name, backup_dir / name):
            copied.append(name)
    for name in FILE_ITEMS:
        if copy_item(PROJECT_ROOT / name, backup_dir / name):
            copied.append(name)

    manifest = backup_dir / "BACKUP_MANIFEST.txt"
    manifest.write_text(
        "\n".join(
            [
                f"Backup created: {datetime.now().isoformat(timespec='seconds')}",
                f"Project root: {PROJECT_ROOT}",
                "",
                "Copied items:",
                *(f"- {item}" for item in copied),
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Created backup: {backup_dir}")
    print(f"Copied {len(copied)} item(s).")
    return backup_dir


def directory_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def list_backups() -> int:
    if not BACKUP_ROOT.exists():
        print("No backups found.")
        return 0
    backups = sorted([path for path in BACKUP_ROOT.iterdir() if path.is_dir()], reverse=True)
    if not backups:
        print("No backups found.")
        return 0
    for backup in backups:
        print(f"{backup.name} | {format_size(directory_size(backup))} | {backup}")
    return 0


def confirm_restore(backup_dir: Path) -> bool:
    print(f"Restore backup: {backup_dir}")
    print("This will replace matching project files and directories with the backup copy.")
    answer = input("Type RESTORE to continue: ").strip()
    return answer == "RESTORE"


def restore_backup(timestamp: str, assume_yes: bool = False) -> int:
    backup_dir = BACKUP_ROOT / timestamp
    if not backup_dir.exists() or not backup_dir.is_dir():
        print(f"Backup not found: {timestamp}")
        return 1
    if not assume_yes and not confirm_restore(backup_dir):
        print("Restore canceled.")
        return 0

    restored: list[str] = []
    for name in DIRECTORY_ITEMS:
        source = backup_dir / name
        target = PROJECT_ROOT / name
        if source.exists():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target, ignore=ignore_patterns)
            restored.append(name)
    for name in FILE_ITEMS:
        source = backup_dir / name
        target = PROJECT_ROOT / name
        if source.exists():
            shutil.copy2(source, target)
            restored.append(name)

    print(f"Restored {len(restored)} item(s) from {backup_dir}.")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "create":
        create_backup()
        return 0
    if args.command == "list":
        return list_backups()
    if args.command == "restore":
        return restore_backup(args.timestamp, args.yes)
    print(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
