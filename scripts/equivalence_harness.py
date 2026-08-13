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

from equivalence_normalize import (
    canonical_json,
    document_record,
    file_sha256,
    normalized_console,
    sha256_text,
)


SCHEMA_VERSION = 1
LOCKED_BASELINE = "a14fb43d58a8cc8f3817fd3ac7665fc913bb22f4"
BASELINE_ID = "a14fb43"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACKED_ROOT = PROJECT_ROOT / "evals" / "equivalence"
TRANSIENT_ROOT = Path(
    os.environ.get("RESUME_EQUIVALENCE_TRANSIENT_ROOT", PROJECT_ROOT / "scratch" / "equivalence")
).resolve()
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


@dataclass(frozen=True)
class ProcessCapture:
    returncode: int
    stdout: str
    stderr: str
    output_dir: Path
    render_dir: Path


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
    # Keep this deliberately short.  Render folders include the complete
    # artifact label, and Windows tools still enforce legacy path limits.
    root = TRANSIENT_ROOT / "r" / f"{label[:1]}{uuid.uuid4().hex[:7]}"
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


def scan_archive_poor_candidates(commit_root: Path) -> tuple[dict[str, Any], ...]:
    """Run the baseline's canonical POOR detector over every archived posting.

    The complete approved source bank is used as the evidence surface.  Any
    candidate is subsequently rebuilt before it can represent POOR; an empty
    result is recorded as a coverage gap, never replaced with a synthetic JD.
    """
    code = r'''
import json, sys
from pathlib import Path
from docx import Document
sys.path.insert(0, sys.argv[1])
import resume_analysis
root = Path(sys.argv[2])
source_text = "\n".join(
    paragraph.text
    for source in sorted((root / "source").glob("*.docx"))
    for paragraph in Document(str(source)).paragraphs
)
records = []
for metadata_path in sorted((root / "scratch" / "jd_library").glob("*/metadata.json")):
    posting = metadata_path.parent / "job_description.txt"
    if not posting.is_file():
        continue
    reasons = resume_analysis.poor_fit_requirements(posting.read_text(encoding="utf-8-sig"), source_text)
    if reasons:
        records.append({"snapshot_id": metadata_path.parent.name, "reasons": list(reasons)})
print(json.dumps(records))
'''
    result = subprocess.run(
        [sys.executable, "-c", code, str(commit_root / "scripts"), str(commit_root)],
        cwd=commit_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if result.returncode:
        raise HarnessError(result.stderr.strip() or "full archive POOR-candidate scan failed")
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise HarnessError("full archive POOR-candidate scan returned invalid data")
    return tuple(payload)


def artifact_state(path: Path) -> str:
    stem = path.stem.upper()
    for state in ("DRAFT", "POOR", "FAIL", "BRIDGE"):
        if f" {state} " in f" {stem} ":
            return state
    return "PASS"


def _empty_input(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def fixture_environment(
    commit_root: Path,
    fixture_root: Path,
    *,
    job_description: Path | None = None,
    federal_job_description: Path | None = None,
    questions: Path | None = None,
) -> tuple[dict[str, str], Path, Path]:
    inputs = fixture_root / "inputs"
    output_dir = fixture_root / "output"
    render_dir = fixture_root / "renders"
    scratch_dir = fixture_root / "scratch"
    output_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    empty_commercial = _empty_input(inputs / "empty_commercial.txt")
    empty_federal = _empty_input(inputs / "empty_federal.txt")
    empty_questions = _empty_input(inputs / "empty_questions.txt")
    empty_research = _empty_input(inputs / "empty_research.txt")
    empty_notes = _empty_input(inputs / "empty_notes.txt")
    env = os.environ.copy()
    env.update(
        {
            "RESUME_PYTHON": sys.executable,
            "RESUME_JOB_DESCRIPTION_PATH": str(job_description or empty_commercial),
            "RESUME_FEDERAL_JOB_DESCRIPTION_PATH": str(federal_job_description or empty_federal),
            "RESUME_APPLICATION_QUESTIONS_PATH": str(questions or empty_questions),
            "RESUME_COMPANY_RESEARCH_PATH": str(empty_research),
            "RESUME_INTERVIEW_NOTES_PATH": str(empty_notes),
            "RESUME_OUTPUT_DIR": str(output_dir),
            "RESUME_RENDER_DIR": str(render_dir),
            "RESUME_SCRATCH_DIR": str(scratch_dir),
            "RESUME_APPLICATIONS_CSV_PATH": str(scratch_dir / "applications.csv"),
            "RESUME_JD_LIBRARY_DIR": str(scratch_dir / "jd_library"),
            "PYTHONPYCACHEPREFIX": str(fixture_root / "pycache"),
            "PYTHONUTF8": "1",
        }
    )
    return env, output_dir, render_dir


def run_fixture_script(
    commit_root: Path,
    fixture_root: Path,
    script_name: str,
    *,
    job_description: Path | None = None,
    federal_job_description: Path | None = None,
    questions: Path | None = None,
    arguments: tuple[str, ...] = (),
    timeout_seconds: int = 600,
) -> ProcessCapture:
    env, output_dir, render_dir = fixture_environment(
        commit_root,
        fixture_root,
        job_description=job_description,
        federal_job_description=federal_job_description,
        questions=questions,
    )
    result = subprocess.run(
        [sys.executable, str(commit_root / "scripts" / script_name), *arguments],
        cwd=commit_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    return ProcessCapture(result.returncode, result.stdout, result.stderr, output_dir, render_dir)


def run_in_environment(
    commit_root: Path,
    env: dict[str, str],
    script_name: str,
    arguments: tuple[str, ...] = (),
    *,
    timeout_seconds: int = 900,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(commit_root / "scripts" / script_name), *arguments],
        cwd=commit_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )


def _render_record(render_root: Path, docx_path: Path, commit_root: Path | None = None) -> dict[str, Any]:
    manifests = sorted(render_root.glob("*/manifest.json"), key=lambda item: item.stat().st_mtime_ns)
    expected_hash = file_sha256(docx_path)
    for manifest_path in reversed(manifests):
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("source_docx_sha256") != expected_hash:
            continue
        names = payload.get("page_filenames")
        if not isinstance(names, list) or not names:
            raise HarnessError(f"render manifest has no page inventory for {docx_path.name}")
        missing = [name for name in names if not (manifest_path.parent / str(name)).is_file()]
        if missing or payload.get("page_count") != len(names):
            raise HarnessError(f"render manifest page inventory is invalid for {docx_path.name}")
        normalized = dict(payload)
        normalized["source_path"] = "<SOURCE_DOCX>"
        normalized["renderer_executable"] = Path(str(payload.get("renderer_executable", ""))).name
        normalized["python_executable"] = Path(str(payload.get("python_executable", ""))).name
        normalized.pop("rendered_at_utc", None)
        return {
            "page_count": len(names),
            "renderer": normalized.get("renderer_executable"),
            "renderer_version": normalized.get("renderer_version"),
            "manifest": normalized,
            "manifest_sha256": sha256_text(canonical_json(normalized)),
        }
    if commit_root is not None:
        fallback = render_root / ("h" + sha256_text(docx_path.name)[:8])
        shutil.rmtree(fallback, ignore_errors=True)
        result = subprocess.run(
            [sys.executable, str(commit_root / "scripts" / "render_docx_windows.py"), str(docx_path), "--output_dir", str(fallback)],
            cwd=commit_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=240,
        )
        if result.returncode:
            raise HarnessError((result.stderr or result.stdout).strip() or f"fallback render failed for {docx_path.name}")
        return _render_record(render_root, docx_path)
    raise HarnessError(f"verified render manifest not found for {docx_path.name}")


def _single_docx(output_dir: Path, pattern: str) -> Path:
    matches = sorted(output_dir.glob(pattern))
    if len(matches) != 1:
        raise HarnessError(f"expected one {pattern} artifact in {output_dir}; found {len(matches)}")
    return matches[0]


def capture_commercial_resume(
    baseline_root: Path,
    run_root: Path,
    lane: str,
    snapshot_id: str,
) -> dict[str, Any]:
    snapshot_dir = baseline_root / "scratch" / "jd_library" / snapshot_id
    job_description = snapshot_dir / "job_description.txt"
    if not job_description.is_file():
        raise HarnessError(f"commercial fixture input is missing: {job_description}")
    questions = snapshot_dir / "application_questions.txt"
    fixture_root = run_root / "f" / sha256_text(snapshot_id)[:8]
    capture = run_fixture_script(
        baseline_root,
        fixture_root,
        "build_resume.py",
        job_description=job_description,
        questions=questions if questions.is_file() else None,
        arguments=("--no-pdf",),
    )
    docx_path = _single_docx(capture.output_dir, "*Resume.docx")
    record = document_record(docx_path)
    record.update(
        {
            "fixture_id": f"commercial_{lane}",
            "snapshot_id": snapshot_id,
            "artifact_type": "resume",
            "artifact_state": artifact_state(docx_path),
            "process": {
                "returncode": capture.returncode,
                "stdout": normalized_console(capture.stdout, (baseline_root, run_root)),
                "stderr": normalized_console(capture.stderr, (baseline_root, run_root)),
            },
            "render": _render_record(capture.render_dir, docx_path, baseline_root),
        }
    )
    return record


def _parse_federal_status(stdout: str) -> dict[str, Any]:
    import re

    match = re.search(
        r"FEDERAL PARSE STATUS:\s*duty_grade=(\S+)\s+selected_grade=(\S+)\s+available_grades=(.*?)\s+selected_requirements=(\d+)\s+verified=(\S+)",
        stdout,
    )
    if not match:
        return {}
    return {
        "duty_grade": match.group(1),
        "selected_grade": match.group(2),
        "available_grades": match.group(3).split(",") if match.group(3) else [],
        "selected_requirements": int(match.group(4)),
        "verified": match.group(5).lower() == "true",
    }


def capture_federal_document_set(
    baseline_root: Path,
    run_root: Path,
    fixture_id: str,
    posting_path: Path,
) -> dict[str, Any]:
    fixture_root = run_root / "f" / sha256_text(fixture_id)[:8]
    capture = run_fixture_script(
        baseline_root,
        fixture_root,
        "build_federal_resume.py",
        federal_job_description=posting_path,
        arguments=("--no-pdf",),
        timeout_seconds=900,
    )
    resume_path = _single_docx(capture.output_dir, "*Federal Resume.docx")
    qualifications_path = _single_docx(capture.output_dir, "*Federal Qualifications Statement.docx")
    documents = []
    for artifact_type, path in (("federal_resume", resume_path), ("federal_qualifications", qualifications_path)):
        item = document_record(path)
        item.update(
            {
                "artifact_type": artifact_type,
                "artifact_state": artifact_state(path),
                "render": _render_record(capture.render_dir, path, baseline_root),
            }
        )
        documents.append(item)
    return {
        "fixture_id": fixture_id,
        "artifact_state": artifact_state(resume_path),
        "posting_sha256": file_sha256(posting_path),
        "federal_parse": _parse_federal_status(capture.stdout),
        "documents": documents,
        "process": {
            "returncode": capture.returncode,
            "stdout": normalized_console(capture.stdout, (baseline_root, run_root)),
            "stderr": normalized_console(capture.stderr, (baseline_root, run_root)),
        },
    }


TRANSACTION_PROBE = r'''
import hashlib, json, subprocess, sys
from pathlib import Path
import workflow_step_runner as runner

root = Path(sys.argv[1])
root.mkdir(parents=True, exist_ok=True)
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

results = {}
success = root / "success"
success.mkdir()
staged_resume = success / "staged_resume.docx"
staged_quals = success / "staged_qualifications.docx"
final_resume = success / "resume.docx"
final_quals = success / "qualifications.docx"
staged_resume.write_bytes(b"new resume")
staged_quals.write_bytes(b"new qualifications")
runner.publish_document_set(((staged_resume, final_resume), (staged_quals, final_quals)), quarantine_root=success / "quarantine")
results["success"] = {
    "resume_sha256": digest(final_resume),
    "qualifications_sha256": digest(final_quals),
    "staged_removed": not staged_resume.exists() and not staged_quals.exists(),
}

rollback = root / "rollback"
rollback.mkdir()
staged_resume = rollback / "staged_resume.docx"
staged_quals = rollback / "staged_qualifications.docx"
final_resume = rollback / "resume.docx"
final_quals = rollback / "qualifications.docx"
staged_resume.write_bytes(b"new resume")
staged_quals.write_bytes(b"new qualifications")
final_resume.write_bytes(b"old resume")
final_quals.write_bytes(b"old qualifications")
original_replace = runner.os.replace
calls = 0
def injected_replace(source, destination):
    global calls
    calls += 1
    if calls == 2:
        raise OSError("injected replacement failure")
    original_replace(source, destination)
runner.os.replace = injected_replace
raised = False
try:
    runner.publish_document_set(((staged_resume, final_resume), (staged_quals, final_quals)), quarantine_root=rollback / "quarantine")
except OSError:
    raised = True
finally:
    runner.os.replace = original_replace
results["rollback"] = {
    "raised": raised,
    "resume_restored": final_resume.read_bytes() == b"old resume",
    "qualifications_restored": final_quals.read_bytes() == b"old qualifications",
}

def workflow_case(case_name, timed_out):
    case = root / case_name
    output = case / "output"
    logs = case / "logs"
    output.mkdir(parents=True)
    original = output / "resume.docx"
    original.write_bytes(b"known-good")
    terminated = []
    class Process:
        pid = 24680 if timed_out else 13579
        returncode = 0 if timed_out else 1
        def __init__(self): self.calls = 0
        def communicate(self, timeout=None):
            self.calls += 1
            if timed_out and self.calls == 1:
                raise subprocess.TimeoutExpired("builder", timeout)
            original.write_bytes(b"partial" if timed_out else b"failed partial")
            return ("partial output", "" if timed_out else "injected builder failure")
    original_popen = runner.subprocess.Popen
    original_terminate = runner.terminate_process_tree
    runner.subprocess.Popen = lambda *_args, **_kwargs: Process()
    runner.terminate_process_tree = lambda process: terminated.append(process.pid)
    try:
        result = runner.run_document_step(
            step_name="Building federal resume",
            command=[sys.executable, "builder.py"],
            cwd=case,
            output_dir=output,
            log_dir=logs,
            timeout_seconds=600,
        )
    finally:
        runner.subprocess.Popen = original_popen
        runner.terminate_process_tree = original_terminate
    quarantined = None
    if result.quarantine_path is not None:
        candidate = result.quarantine_path / "resume.docx"
        quarantined = candidate.read_text(encoding="utf-8") if candidate.is_file() else None
    return {
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "terminated": terminated,
        "original_restored": original.read_bytes() == b"known-good",
        "quarantined_content": quarantined,
    }

results["timeout_quarantine"] = workflow_case("timeout", True)
results["nonzero_quarantine"] = workflow_case("nonzero", False)
print(json.dumps(results, sort_keys=True))
'''


def capture_transaction_probes(baseline_root: Path, run_root: Path) -> dict[str, Any]:
    probe_root = run_root / "p"
    probe_root.mkdir(parents=True, exist_ok=True)
    probe_path = probe_root / "probe.py"
    probe_path.write_text(TRANSACTION_PROBE, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(baseline_root / "scripts")
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, str(probe_path), str(probe_root / "state")],
        cwd=baseline_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if result.returncode:
        raise HarnessError(result.stderr.strip() or "federal transaction probe failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise HarnessError(f"federal transaction probe returned invalid JSON: {error}") from error
    expected = (
        payload.get("success", {}).get("resume_sha256")
        and payload.get("rollback", {}).get("raised") is True
        and payload.get("rollback", {}).get("resume_restored") is True
        and payload.get("rollback", {}).get("qualifications_restored") is True
        and payload.get("timeout_quarantine", {}).get("returncode") == 124
        and payload.get("timeout_quarantine", {}).get("original_restored") is True
        and payload.get("timeout_quarantine", {}).get("quarantined_content") == "partial"
        and payload.get("nonzero_quarantine", {}).get("returncode") == 1
        and payload.get("nonzero_quarantine", {}).get("original_restored") is True
    )
    if not expected:
        raise HarnessError("federal transaction probe did not preserve the Release A recovery contract")
    return {
        "fixture_id": "federal_transactional_behavior",
        "step_result": {"availability": "not_present_at_release_a"},
        "outcomes": payload,
    }


def capture_federal_fixtures(baseline_root: Path, run_root: Path) -> list[dict[str, Any]]:
    fixture_dir = baseline_root / "scripts" / "test_fixtures" / "federal"
    single = fixture_dir / "verified_single_grade.txt"
    multi = fixture_dir / "dhs_multi_grade.txt"
    if not single.is_file() or not multi.is_file():
        raise HarnessError("tracked federal parser fixtures are missing")
    ai_control = run_root / "i" / "federal_ai_control.txt"
    ai_control.parent.mkdir(parents=True, exist_ok=True)
    ai_control.write_text(
        single.read_text(encoding="utf-8-sig")
        + "\nThe role uses generative AI to support secure program analysis and documentation.\n",
        encoding="utf-8",
    )
    records = [
        capture_federal_document_set(baseline_root, run_root, "federal_single_grade_standard", single),
        capture_federal_document_set(baseline_root, run_root, "federal_multi_grade_standard", multi),
        capture_federal_document_set(baseline_root, run_root, "federal_single_grade_ai_control", ai_control),
        capture_transaction_probes(baseline_root, run_root),
    ]
    standard_text = records[0]["documents"][0]["visible_text"]
    ai_text = records[2]["documents"][0]["visible_text"]
    if standard_text == ai_text or "AI-assisted documentation" not in ai_text:
        raise HarnessError("controlled federal AI fixture did not exercise the AI summary branch")
    states = {record.get("artifact_state") for record in records if record.get("artifact_state")}
    if "DRAFT" not in states:
        raise HarnessError("federal fixtures did not produce required DRAFT coverage")
    return records


def capture_companion_set(
    baseline_root: Path,
    run_root: Path,
    fixture_id: str,
    snapshot_id: str,
) -> dict[str, Any]:
    snapshot = baseline_root / "scratch" / "jd_library" / snapshot_id
    fixture_root = run_root / "c" / sha256_text(fixture_id)[:8]
    env, output_dir, render_dir = fixture_environment(
        baseline_root,
        fixture_root,
        job_description=snapshot / "job_description.txt",
        questions=(snapshot / "application_questions.txt") if (snapshot / "application_questions.txt").is_file() else None,
    )
    commands = (
        ("resume", "build_resume.py", ("--no-pdf",)),
        ("cover", "build_cover_letter.py", ("--mode", "standard")),
        ("qualifications", "build_standard_qualifications_statement.py", ()),
        ("interview", "build_interview_cheat_sheet.py", ()),
        ("guide", "build_detailed_interview_guide.py", ()),
    )
    processes = []
    for label, script, arguments in commands:
        result = run_in_environment(baseline_root, env, script, arguments)
        processes.append(
            {
                "label": label,
                "returncode": result.returncode,
                "stdout": normalized_console(result.stdout, (baseline_root, run_root)),
                "stderr": normalized_console(result.stderr, (baseline_root, run_root)),
            }
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            raise HarnessError(f"{fixture_id} companion command {label} failed with {result.returncode}{suffix}")
    documents = []
    for path in sorted(output_dir.glob("*.docx")):
        record = document_record(path)
        record["artifact_state"] = artifact_state(path)
        record["render"] = _render_record(render_dir, path, baseline_root)
        documents.append(record)
    expected_terms = ("Resume", "Cover Letter", "Qualifications Statement", "Interview Cheat Sheet", "Detailed Interview Guide")
    for term in expected_terms:
        if not any(term in item["filename"] for item in documents):
            raise HarnessError(f"{fixture_id} did not produce {term}")
    return {
        "fixture_id": fixture_id,
        "snapshot_id": snapshot_id,
        "documents": documents,
        "processes": processes,
    }


SYSTEM_PROBE = r'''
import contextlib, io, json, os, shutil, sys, time
from pathlib import Path
import application_status, job_context_archive, track_applications

root = Path(sys.argv[1])
job = Path(os.environ["RESUME_JOB_DESCRIPTION_PATH"])
output = Path(os.environ["RESUME_OUTPUT_DIR"])
tracker = Path(os.environ["RESUME_APPLICATIONS_CSV_PATH"])
library = Path(os.environ["RESUME_JD_LIBRARY_DIR"])
job.write_text("Company: Probe Company\nRole: Implementation Consultant\nResponsibilities\n- Lead ERP implementation delivery.\n", encoding="utf-8")
output.mkdir(parents=True, exist_ok=True)
library.mkdir(parents=True, exist_ok=True)

states = {}
for state, suffix in (("READY", ""), ("REVIEW", " BRIDGE"), ("BLOCKED", " FAIL")):
    for path in output.glob("*.docx"): path.unlink()
    resume = output / f"Christian Estrada - Probe Company - Implementation Consultant{suffix} Resume.docx"
    resume.write_bytes(b"probe")
    report = application_status.build_report(job.read_text(encoding="utf-8"), ("resume",))
    states[state] = {"overall": report.overall_state, "resume_status": report.artifacts[0].status}
for path in output.glob("*.docx"): path.unlink()
missing = application_status.build_report(job.read_text(encoding="utf-8"), ("resume",))
states["MISSING"] = missing.artifacts[0].status
resume = output / "Christian Estrada - Probe Company - Implementation Consultant Resume.docx"
resume.write_bytes(b"probe")
optional = application_status.build_report(job.read_text(encoding="utf-8"), ("resume",))
states["NOT_BUILT"] = {r.artifact_type:r.status for r in optional.artifacts if r.status == "NOT BUILT"}
cover = output / "Christian Estrada - Probe Company - Implementation Consultant Cover Letter.docx"
cover.write_bytes(b"probe cover")
os.utime(cover, (time.time() - 100, time.time() - 100))
os.utime(resume, None)
stale = application_status.build_report(job.read_text(encoding="utf-8"), ("resume", "cover"))
states["STALE"] = next(r.status for r in stale.artifacts if r.artifact_type == "cover")

snapshot = job_context_archive.archive_active_context(source_command="equivalence", archive_reason="probe")
results = {"readiness": states, "snapshot_id_present": bool(snapshot)}
print(json.dumps(results, sort_keys=True))
'''


def capture_system_behavior(baseline_root: Path, run_root: Path) -> dict[str, Any]:
    fixture_root = run_root / "s"
    env, output_dir, _render_dir = fixture_environment(baseline_root, fixture_root)
    probe = fixture_root / "probe.py"
    probe.write_text(SYSTEM_PROBE, encoding="utf-8")
    env["PYTHONPATH"] = str(baseline_root / "scripts")
    result = subprocess.run(
        [sys.executable, str(probe), str(fixture_root)], cwd=baseline_root, env=env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace", timeout=60,
    )
    if result.returncode:
        raise HarnessError(result.stderr.strip() or "system behavior probe failed")
    payload = json.loads(result.stdout)
    expected = payload.get("readiness", {})
    if expected.get("READY", {}).get("overall") != "READY" or expected.get("BLOCKED", {}).get("overall") != "BLOCKED":
        raise HarnessError("readiness system probe did not cover READY and BLOCKED")

    baseline_library = baseline_root / "scratch" / "jd_library"
    isolated_library = Path(env["RESUME_JD_LIBRARY_DIR"])
    if isolated_library.exists():
        shutil.rmtree(isolated_library)
    shutil.copytree(baseline_library, isolated_library)
    refresh = run_in_environment(baseline_root, env, "build_jd_library.py", ("refresh-metadata",), timeout_seconds=300)
    if refresh.returncode:
        raise HarnessError("isolated jd-archive-refresh failed")
    snapshots = commercial_fixture_plan(baseline_root)["selected_snapshots"]
    queue_dir = fixture_root / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    for index, lane in enumerate(("implementation_delivery", "change_enablement"), start=1):
        source = baseline_root / "scratch" / "jd_library" / snapshots[lane] / "job_description.txt"
        shutil.copy2(source, queue_dir / f"{index:02d}_{lane}.txt")
    queue_state = fixture_root / "queue_state"
    queue_output = fixture_root / "queue_output"
    queue_render = fixture_root / "queue_render"
    queue = run_in_environment(
        baseline_root,
        env,
        "run_commercial_queue.py",
        (
            "--resume-only", "--queue-dir", str(queue_dir), "--state-root", str(queue_state),
            "--output-dir", str(queue_output), "--render-dir", str(queue_render),
        ),
        timeout_seconds=1200,
    )
    if queue.returncode:
        raise HarnessError(f"two-posting queue failed with {queue.returncode}")
    manifests = sorted(queue_state.glob("**/*.json"))
    queue_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in manifests]
    return {
        "fixture_id": "system_readiness_tracker_archive",
        "payload": payload,
        "archive_refresh": {
            "returncode": refresh.returncode,
            "stdout": normalized_console(refresh.stdout, (baseline_root, run_root)),
            "stderr": normalized_console(refresh.stderr, (baseline_root, run_root)),
            "snapshot_count": len(list(isolated_library.glob("*/metadata.json"))),
        },
        "queue": {
            "returncode": queue.returncode,
            "stdout": normalized_console(queue.stdout, (baseline_root, run_root)),
            "stderr": normalized_console(queue.stderr, (baseline_root, run_root)),
            "manifest_payloads": queue_payloads,
            "resume_count": len(list(queue_output.glob("*Resume.docx"))),
        },
    }


def capture_companion_and_system_fixtures(
    baseline_root: Path,
    run_root: Path,
    commercial_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for state in ("PASS", "BRIDGE", "FAIL"):
        representative = next(item for item in commercial_records if item["artifact_state"] == state)
        records.append(
            capture_companion_set(
                baseline_root,
                run_root,
                f"companion_{state.lower()}",
                representative["snapshot_id"],
            )
        )
    records.append(capture_system_behavior(baseline_root, run_root))
    return records


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def capture_behavior(baseline_revision: str) -> dict[str, Any]:
    started = time.monotonic()
    run_root = new_run_root("capture")
    try:
        baseline = export_commit(baseline_revision, run_root / "b")
        plan = commercial_fixture_plan(baseline.root)
        records = [
            capture_commercial_resume(baseline.root, run_root, lane, snapshot_id)
            for lane, snapshot_id in plan["selected_snapshots"].items()
        ]
        federal_records = capture_federal_fixtures(baseline.root, run_root)
        companion_records = capture_companion_and_system_fixtures(baseline.root, run_root, records)
        observed_states = sorted({record["artifact_state"] for record in records})
        poor_candidates = scan_archive_poor_candidates(baseline.root)
        representatives = {
            state: next(
                (record["fixture_id"] for record in records if record["artifact_state"] == state),
                None,
            )
            for state in ("PASS", "BRIDGE", "FAIL", "POOR")
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "baseline_sha": baseline.sha,
            "baseline_id": BASELINE_ID if baseline.sha == LOCKED_BASELINE else baseline.sha[:8],
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.monotonic() - started, 3),
            "fixture_plan": plan,
            "coverage": {
                "observed_commercial_states": observed_states,
                "missing_required_commercial_states": sorted({"PASS", "BRIDGE", "FAIL"} - set(observed_states)),
                "state_representatives": representatives,
                "poor": (
                    "represented"
                    if "POOR" in observed_states
                    else "coverage_gap_no_canonical_candidates_in_full_archive"
                    if not poor_candidates
                    else "candidate_requires_full_rebuild"
                ),
                "poor_candidate_scan_count": len(poor_candidates),
                "poor_candidates": list(poor_candidates),
            },
            "records": [*records, *federal_records, *companion_records],
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
                payload = capture_behavior(args.baseline)
                report_path = TRANSIENT_ROOT / "reports" / f"capture_{payload['baseline_id']}.json"
                write_json(report_path, payload)
                print(f"Captured {len(payload['records'])} fixture(s) for {payload['baseline_sha']}")
                print(f"Report: {report_path}")
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
