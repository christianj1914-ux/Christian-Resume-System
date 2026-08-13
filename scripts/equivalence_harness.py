#!/usr/bin/env python3
"""Capture and compare exact-commit behavioral fixtures for Release B prep."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from equivalence_normalize import canonical_json, file_sha256, sha256_text


SCHEMA_VERSION = 1
LOCKED_BASELINE = "a14fb43d58a8cc8f3817fd3ac7665fc913bb22f4"
BASELINE_ID = "a14fb43"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACKED_ROOT = PROJECT_ROOT / "evals" / "equivalence"
TRANSIENT_ROOT = PROJECT_ROOT / "scratch" / "equivalence"
PROTECTED_FILES = (
    Path("jobs/job_description.txt"),
    Path("jobs/federal_job_description.txt"),
    Path("jobs/application_questions.txt"),
    Path("jobs/company_research.txt"),
    Path("jobs/interview_notes.txt"),
    Path("scratch/applications.csv"),
    Path("scratch/jd_library/index.csv"),
)
PROTECTED_TREES = (Path("output"), Path("scratch/jd_library"))


class HarnessError(RuntimeError):
    """A capture failed before a meaningful equivalence result existed."""


@dataclass(frozen=True)
class CommitExport:
    sha: str
    root: Path


def run_git(*args: str, cwd: Path = PROJECT_ROOT) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise HarnessError((result.stderr or result.stdout).strip() or f"git {' '.join(args)} failed")
    return result.stdout.rstrip("\r\n")


def resolve_commit(revision: str) -> str:
    return run_git("rev-parse", "--verify", f"{revision}^{{commit}}")


def dirty_paths() -> tuple[str, ...]:
    output = run_git("status", "--porcelain", "--untracked-files=all")
    return tuple(line[3:] for line in output.splitlines() if len(line) > 3)


def new_run_root(label: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = TRANSIENT_ROOT / "runs" / f"{stamp}_{label}_{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def export_commit(revision: str, destination: Path) -> CommitExport:
    sha = resolve_commit(revision)
    destination.mkdir(parents=True, exist_ok=False)
    archive_path = destination.parent / f"{destination.name}.zip"
    result = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "archive", "--format=zip", f"--output={archive_path}", sha],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise HarnessError((result.stderr or result.stdout).strip() or f"could not export {sha}")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(destination)
    finally:
        archive_path.unlink(missing_ok=True)
    return CommitExport(sha=sha, root=destination)


def _tree_payload(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    payload = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix().lower()):
        payload.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    return payload


def protected_snapshot(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for relative in PROTECTED_FILES:
        path = project_root / relative
        files[relative.as_posix()] = file_sha256(path) if path.is_file() else None
    trees = {
        relative.as_posix(): sha256_text(canonical_json(_tree_payload(project_root / relative)))
        for relative in PROTECTED_TREES
    }
    return {"files": files, "trees": trees}


@contextlib.contextmanager
def isolation_guard(project_root: Path = PROJECT_ROOT) -> Iterator[dict[str, Any]]:
    before = protected_snapshot(project_root)
    yield before
    after = protected_snapshot(project_root)
    if before != after:
        changed = sorted(
            key
            for section in ("files", "trees")
            for key in set(before[section]) | set(after[section])
            if before[section].get(key) != after[section].get(key)
        )
        raise HarnessError("capture mutated protected workspace state: " + ", ".join(changed))


def read_targeting_lanes(commit_root: Path) -> tuple[str, ...]:
    code = (
        "import json,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "from config.job_profiles import TARGETING_LANES;"
        "print(json.dumps([item['key'] for item in TARGETING_LANES]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(commit_root / "scripts")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        cwd=commit_root,
    )
    if result.returncode:
        raise HarnessError(result.stderr.strip() or "could not load targeting lanes")
    lanes = json.loads(result.stdout)
    if not isinstance(lanes, list) or not all(isinstance(item, str) and item for item in lanes):
        raise HarnessError("TARGETING_LANES returned an invalid lane inventory")
    return tuple(lanes)


def archived_snapshots(commit_root: Path) -> tuple[dict[str, Any], ...]:
    library = commit_root / "scratch" / "jd_library"
    snapshots: list[dict[str, Any]] = []
    for metadata_path in sorted(library.glob("*/metadata.json"), key=lambda item: item.parent.name):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise HarnessError(f"invalid archive metadata {metadata_path}: {error}") from error
        metadata["snapshot_dir"] = str(metadata_path.parent)
        snapshots.append(metadata)
    return tuple(snapshots)


def commercial_fixture_plan(commit_root: Path) -> dict[str, Any]:
    lanes = read_targeting_lanes(commit_root)
    snapshots = archived_snapshots(commit_root)
    selected: dict[str, str] = {}
    for lane in lanes:
        matches = sorted(
            str(item.get("snapshot_id", ""))
            for item in snapshots
            if item.get("lane") == lane and item.get("snapshot_id")
        )
        if not matches:
            raise HarnessError(f"missing archived snapshot for live lane: {lane}")
        selected[lane] = matches[0]
    historical = sorted(
        {
            str(item.get("lane"))
            for item in snapshots
            if item.get("lane") and item.get("lane") not in lanes
        }
    )
    return {
        "live_lanes": list(lanes),
        "selected_snapshots": selected,
        "historical_archive_lanes": historical,
        "archive_snapshot_count": len(snapshots),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def capture_foundation(baseline_revision: str) -> dict[str, Any]:
    started = time.monotonic()
    run_root = new_run_root("capture")
    try:
        baseline = export_commit(baseline_revision, run_root / "baseline")
        plan = commercial_fixture_plan(baseline.root)
        return {
            "schema_version": SCHEMA_VERSION,
            "baseline_sha": baseline.sha,
            "baseline_id": BASELINE_ID if baseline.sha == LOCKED_BASELINE else baseline.sha[:8],
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.monotonic() - started, 3),
            "fixture_plan": plan,
            "step_result": {"availability": "not_present_at_release_a"},
        }
    finally:
        shutil.rmtree(run_root, ignore_errors=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture and compare Release A output equivalence fixtures.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--baseline", default=LOCKED_BASELINE)
    compare = subparsers.add_parser("compare")
    compare.add_argument("--baseline", default=BASELINE_ID)
    compare.add_argument("--candidate", default="HEAD")
    compare.add_argument("--fixture")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        changed = dirty_paths()
        if changed:
            print("Workspace edits are excluded from equivalence evaluation:")
            for path in changed:
                print(f"  {path}")
        with isolation_guard():
            if args.command == "capture":
                payload = capture_foundation(args.baseline)
                print(json.dumps(payload, indent=2, sort_keys=True))
                return 0
            candidate_sha = resolve_commit(args.candidate)
            baseline_dir = TRACKED_ROOT / args.baseline
            if not baseline_dir.is_dir():
                raise HarnessError(f"baseline is not frozen: {baseline_dir}")
            print(f"EQUIVALENCE baseline={args.baseline} candidate={candidate_sha}")
            raise HarnessError("comparison records are not implemented yet")
    except HarnessError as error:
        print(f"EQUIVALENCE HARNESS ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
