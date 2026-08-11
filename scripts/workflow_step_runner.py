"""Shared timeout-safe subprocess execution for document workflow steps."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ProcessStepResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    quarantine_path: Path | None = None


def output_docx_snapshot(output_dir: Path) -> tuple[Path, dict[Path, tuple[int, int]]]:
    """Preserve existing outputs so a killed writer cannot replace a usable DOCX."""
    backup_root = Path(tempfile.mkdtemp(prefix="workflow_output_snapshot_"))
    snapshot: dict[Path, tuple[int, int]] = {}
    if not output_dir.exists():
        return backup_root, snapshot
    for document in output_dir.glob("*.docx"):
        stat = document.stat()
        snapshot[document] = (stat.st_mtime_ns, stat.st_size)
        shutil.copy2(document, backup_root / document.name)
    return backup_root, snapshot


def quarantine_timed_out_outputs(
    step_name: str,
    output_dir: Path,
    log_dir: Path,
    backup_root: Path,
    before: dict[Path, tuple[int, int]],
) -> Path | None:
    changed = [
        document
        for document in (output_dir.glob("*.docx") if output_dir.exists() else ())
        if before.get(document) != (document.stat().st_mtime_ns, document.stat().st_size)
    ]
    if not changed:
        shutil.rmtree(backup_root, ignore_errors=True)
        return None
    quarantine = log_dir / "quarantine" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    quarantine.mkdir(parents=True, exist_ok=True)
    for document in changed:
        shutil.move(str(document), str(quarantine / document.name))
    for original in before:
        saved = backup_root / original.name
        if saved.exists() and not original.exists():
            shutil.copy2(saved, original)
    shutil.rmtree(backup_root, ignore_errors=True)
    return quarantine


def quarantine_changed_outputs(
    step_name: str,
    output_dir: Path,
    log_dir: Path,
    backup_root: Path,
    before: dict[Path, tuple[int, int]],
) -> Path | None:
    return quarantine_timed_out_outputs(step_name, output_dir, log_dir, backup_root, before)


def publish_document_set(
    mappings: tuple[tuple[Path, Path], ...],
    *,
    quarantine_root: Path,
) -> None:
    """Commit a staged DOCX set together, restoring every prior file on error."""
    if not mappings:
        return
    destinations = [destination.resolve() for _staged, destination in mappings]
    if len(destinations) != len(set(destinations)):
        raise ValueError("Document-set publication destinations must be unique.")
    transaction = uuid.uuid4().hex
    prepared: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    touched: list[Path] = []
    try:
        for staged, destination in mappings:
            if not staged.is_file():
                raise FileNotFoundError(f"Staged document does not exist: {staged}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            prepared_path = destination.parent / f".{destination.name}.{transaction}.publish"
            shutil.copy2(staged, prepared_path)
            prepared[destination] = prepared_path

        for _staged, destination in mappings:
            backup_path = destination.parent / f".{destination.name}.{transaction}.backup"
            if destination.exists():
                os.replace(destination, backup_path)
                backups[destination] = backup_path
            touched.append(destination)
            os.replace(prepared[destination], destination)
    except Exception:
        quarantine = quarantine_root / datetime.now().strftime("%Y%m%d_%H%M%S_%f_publish_failure")
        quarantine.mkdir(parents=True, exist_ok=True)
        for destination in reversed(touched):
            if destination.exists():
                os.replace(destination, quarantine / destination.name)
            backup_path = backups.get(destination)
            if backup_path and backup_path.exists():
                os.replace(backup_path, destination)
        for destination, backup_path in backups.items():
            if destination not in touched and backup_path.exists():
                os.replace(backup_path, destination)
        raise
    else:
        for backup_path in backups.values():
            backup_path.unlink(missing_ok=True)
    finally:
        for prepared_path in prepared.values():
            prepared_path.unlink(missing_ok=True)


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Terminate the process group so renderer grandchildren cannot retain locks."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def run_document_step(
    *,
    step_name: str,
    command: list[str],
    cwd: Path,
    output_dir: Path,
    log_dir: Path,
    timeout_seconds: int,
) -> ProcessStepResult:
    """Run one document builder with a timeout and recoverable output quarantine."""
    backup_root, before_outputs = output_docx_snapshot(output_dir)
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        start_new_session=os.name != "nt",
    )
    timed_out = False
    quarantine_path: Path | None = None
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        terminate_process_tree(process)
        stdout, stderr = process.communicate()
        stderr = (stderr or "").rstrip() + f"\nERROR: workflow step timed out after {timeout_seconds} seconds.\n"
        quarantine_path = quarantine_changed_outputs(
            step_name,
            output_dir,
            log_dir,
            backup_root,
            before_outputs,
        )
    else:
        if process.returncode:
            quarantine_path = quarantine_changed_outputs(
                step_name,
                output_dir,
                log_dir,
                backup_root,
                before_outputs,
            )
        else:
            shutil.rmtree(backup_root, ignore_errors=True)
    return ProcessStepResult(
        returncode=124 if timed_out else (process.returncode if process.returncode is not None else 1),
        stdout=stdout or "",
        stderr=stderr or "",
        timed_out=timed_out,
        quarantine_path=quarantine_path,
    )
