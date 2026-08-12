#!/usr/bin/env python3
"""Build keyword-policy corpora without touching active jobs or output deliverables."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
import zipfile
from xml.etree import ElementTree as ET

from config.paths import PYTHON_EXECUTABLE


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
JD_LIBRARY = PROJECT_ROOT / "scratch" / "jd_library"
ACTIVE_JOB_FILES = (
    PROJECT_ROOT / "jobs" / "job_description.txt",
    PROJECT_ROOT / "jobs" / "application_questions.txt",
)
ACTIVE_OUTPUT_DIR = PROJECT_ROOT / "output"


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    if path.exists():
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def directory_inventory_digest(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        return digest.hexdigest()
    for candidate in sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: str(item).lower()):
        digest.update(candidate.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_digest(candidate).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def pipeline_fingerprint() -> str:
    measurement_only = {
        "balanced_promotion_report.py",
        "fresh_corpus_rebuild.py",
        "keyword_reliability_corpus.py",
        "smoke_test.py",
    }
    candidates = [
        *sorted(
            path
            for path in (PROJECT_ROOT / "scripts").rglob("*.py")
            if path.name not in measurement_only
        ),
        PROJECT_ROOT / "source" / "evidence_terms.py",
        PROJECT_ROOT / "source" / "Estrada_Resume_Implementation.docx",
        PROJECT_ROOT / "source" / "Estrada_Resume_PreSales_CSM.docx",
        PROJECT_ROOT / "source" / "Christian_Estrada_KPMG_Final_Tightened_EdFix.docx",
        PROJECT_ROOT / "AGENTS.md",
    ]
    digest = hashlib.sha256()
    for candidate in candidates:
        if not candidate.exists():
            continue
        digest.update(candidate.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_digest(candidate).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def page_count(path: Path) -> int:
    try:
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read("docProps/app.xml"))
        node = next((item for item in root.iter() if item.tag.endswith("Pages")), None)
        return int(node.text) if node is not None and node.text else 0
    except Exception:
        return 0


def rendered_page_count(render_dir: Path) -> int:
    candidates = sorted(
        (item for item in render_dir.glob("*") if item.is_dir()),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        count = len(list(candidate.glob("page-*.png")))
        if count:
            return count
    return 0


def logged_page_count(log_path: Path) -> int:
    if not log_path.exists():
        return 0
    matches = re.findall(
        r"Fit render:.*?\bpages=(\d+)\b",
        log_path.read_text(encoding="utf-8", errors="replace"),
    )
    return int(matches[-1]) if matches else 0


def normalize_result_page_count(result: dict[str, Any], result_path: Path) -> dict[str, Any]:
    render_pages = rendered_page_count(result_path.parent / "render_check")
    logged_pages = logged_page_count(result_path.parent / "build.log")
    diagnostic_docx_pages = 0
    resume_path = Path(str(result.get("resume_path", "")))
    if resume_path.is_file():
        diagnostic_docx_pages = page_count(resume_path)
    result["diagnostic_docx_pages"] = diagnostic_docx_pages
    if render_pages and logged_pages and render_pages != logged_pages:
        result.update(
            {
                "exit_state": "failed",
                "error": (
                    "authoritative page-count disagreement: "
                    f"render_images={render_pages}, fit_render_log={logged_pages}"
                ),
                "page_count": 0,
                "page_count_source": "disagreement",
            }
        )
    elif render_pages:
        result["page_count"] = render_pages
        result["page_count_source"] = "render_images"
    elif logged_pages:
        result["page_count"] = logged_pages
        result["page_count_source"] = "fit_render_log"
    else:
        result.update(
            {
                "exit_state": "failed",
                "error": "no authoritative render-based page count was produced",
                "page_count": 0,
                "page_count_source": "missing",
            }
        )
    atomic_write_json(result_path, result)
    return result


def notes_path_for_resume(resume_path: Path) -> Path:
    return resume_path.with_name(
        resume_path.name.replace(" Resume.docx", " Resume Notes.txt")
    )


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if temporary.read_bytes()[:1] != b"{":
        raise ValueError(f"JSON output is not BOM-free UTF-8: {temporary}")
    os.replace(temporary, path)


def worker_main(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    job_path = Path(config["job_description"])
    output_dir = Path(config["output_dir"])
    scratch_dir = Path(config["scratch_dir"])
    render_dir = Path(config["render_dir"])
    result_path = Path(config["result_path"])
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(SCRIPTS_DIR))
    import config.paths as configured_paths  # type: ignore

    configured_paths.JOB_DESCRIPTION = job_path
    configured_paths.OUTPUT_DIR = output_dir
    configured_paths.SCRATCH_DIR = scratch_dir
    os.environ["RESUME_KEYWORD_POLICY"] = "advisory"

    import build_resume  # type: ignore

    # Imports bind path constants by value, so set both the shared config and
    # the already-imported modules before any build work starts.
    build_resume.JOB_DESCRIPTION = job_path
    build_resume.OUTPUT_DIR = output_dir
    build_resume.SCRATCH_DIR = scratch_dir
    build_resume.render_checks.OUTPUT_DIR = output_dir
    build_resume.render_checks.RENDER_ROOT = render_dir

    started = datetime.now().astimezone()
    payload: dict[str, Any] = {
        "fixture": config["fixture"],
        "corpus": config["corpus"],
        "population": "fresh_rebuild",
        "pipeline_fingerprint": config["pipeline_fingerprint"],
        "build_started": started.isoformat(),
        "exit_state": "failed",
    }
    try:
        result = build_resume.build_resume("advisory")
        notes_path = notes_path_for_resume(result.output_docx)
        render_pages = rendered_page_count(render_dir)
        payload.update(
            {
                "exit_state": "success",
                "build_finished": datetime.now().astimezone().isoformat(),
                "source_lane": result.source_resume.name,
                "resume_path": str(result.output_docx.resolve()),
                "notes_path": str(notes_path.resolve()) if notes_path.exists() else "",
                "page_count": render_pages,
                "page_count_source": "render_images" if render_pages else "pending_parent_audit",
                "diagnostic_docx_pages": page_count(result.output_docx),
                "fit": result.audit_status,
                "tailoring": result.tailoring_status,
                "packaged_audit_passed": True,
            }
        )
        atomic_write_json(result_path, payload)
        return 0
    except Exception as exc:
        payload.update(
            {
                "build_finished": datetime.now().astimezone().isoformat(),
                "error": f"{type(exc).__name__}: {exc}",
                "packaged_audit_passed": False,
            }
        )
        atomic_write_json(result_path, payload)
        raise


def fixture_names(corpora: tuple[str, ...]) -> list[tuple[str, str]]:
    sys.path.insert(0, str(SCRIPTS_DIR))
    import keyword_reliability_corpus  # type: ignore

    selected: list[tuple[str, str]] = []
    for corpus in corpora:
        names = (
            keyword_reliability_corpus.RECENT_FIXTURES
            if corpus == "recent"
            else keyword_reliability_corpus.legacy_fixtures()
        )
        selected.extend((corpus, fixture) for fixture in names)
    return selected


def worker_config(
    batch_dir: Path,
    corpus: str,
    fixture: str,
    fingerprint: str,
    ordinal: int = 0,
) -> tuple[Path, Path]:
    fixture_key = hashlib.sha256(f"{corpus}:{fixture}".encode("utf-8")).hexdigest()[:12]
    fixture_dir = batch_dir / corpus / f"{ordinal:02d}_{fixture_key}"
    input_dir = fixture_dir / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    source_dir = JD_LIBRARY / fixture
    job_source = source_dir / "job_description.txt"
    if not job_source.exists():
        raise FileNotFoundError(f"Missing fixture job description: {job_source}")
    job_target = input_dir / "job_description.txt"
    job_target.write_bytes(job_source.read_bytes())
    questions_source = source_dir / "application_questions.txt"
    questions_target = input_dir / "application_questions.txt"
    questions_target.write_bytes(questions_source.read_bytes() if questions_source.exists() else b"")
    result_path = fixture_dir / "result.json"
    config_path = fixture_dir / "worker_config.json"
    atomic_write_json(
        config_path,
        {
            "fixture": fixture,
            "corpus": corpus,
            "pipeline_fingerprint": fingerprint,
            "job_description": str(job_target.resolve()),
            "application_questions": str(questions_target.resolve()),
            "output_dir": str((fixture_dir / "output").resolve()),
            "scratch_dir": str((fixture_dir / "scratch").resolve()),
            "render_dir": str((fixture_dir / "render_check").resolve()),
            "result_path": str(result_path.resolve()),
        },
    )
    return config_path, result_path


def reusable_result(result_path: Path, fingerprint: str) -> dict[str, Any] | None:
    if not result_path.exists():
        return None
    try:
        result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    resume_path = Path(str(result.get("resume_path", "")))
    if (
        result.get("exit_state") == "success"
        and result.get("pipeline_fingerprint") == fingerprint
        and resume_path.is_file()
    ):
        return result
    return None


def run_worker(config_path: Path, log_path: Path) -> int:
    command = [
        str(PYTHON_EXECUTABLE),
        str(Path(__file__).resolve()),
        "--worker-config",
        str(config_path),
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log_path.write_text(completed.stdout, encoding="utf-8")
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", action="append", choices=("recent", "legacy20"))
    parser.add_argument("--batch-dir", type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--fixture", action="append", help="Build only the named fixture; repeat as needed.")
    parser.add_argument("--worker-config", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_config:
        return worker_main(args.worker_config)

    corpora = tuple(dict.fromkeys(args.corpus or ("recent", "legacy20")))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = (args.batch_dir or PROJECT_ROOT / "scratch" / f"fresh_keyword_corpus_{timestamp}").resolve()
    batch_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = batch_dir / "manifest.json"
    fingerprint = pipeline_fingerprint()
    before = {
        "job_files": {str(path): file_digest(path) for path in ACTIVE_JOB_FILES},
        "output_inventory": directory_inventory_digest(ACTIVE_OUTPUT_DIR),
    }
    items = fixture_names(corpora)
    if args.fixture:
        requested = set(args.fixture)
        items = [item for item in items if item[1] in requested]
        missing = requested - {fixture for _corpus, fixture in items}
        if missing:
            parser.error("Unknown fixture(s): " + ", ".join(sorted(missing)))
    results: dict[str, dict[str, Any]] = {}
    pending: list[tuple[str, str, Path, Path]] = []

    for ordinal, (corpus, fixture) in enumerate(items, start=1):
        config_path, result_path = worker_config(
            batch_dir,
            corpus,
            fixture,
            fingerprint,
            ordinal,
        )
        reused = reusable_result(result_path, fingerprint)
        key = f"{corpus}:{fixture}"
        if reused is not None:
            results[key] = normalize_result_page_count(reused, result_path)
        else:
            pending.append((corpus, fixture, config_path, result_path))

    def checkpoint() -> None:
        ordered = [results.get(f"{corpus}:{fixture}", {"fixture": fixture, "corpus": corpus, "exit_state": "pending"})
                   for corpus, fixture in items]
        atomic_write_json(
            manifest_path,
            {
                "schema_version": 1,
                "population": "fresh_rebuild",
                "created": datetime.now().astimezone().isoformat(),
                "pipeline_fingerprint": fingerprint,
                "expected_fixtures": len(items),
                "active_state_before": before,
                "fixtures": ordered,
            },
        )

    checkpoint()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(run_worker, config_path, result_path.parent / "build.log"): (
                corpus,
                fixture,
                result_path,
            )
            for corpus, fixture, config_path, result_path in pending
        }
        for future in as_completed(futures):
            corpus, fixture, result_path = futures[future]
            return_code = future.result()
            key = f"{corpus}:{fixture}"
            if result_path.exists():
                results[key] = normalize_result_page_count(
                    json.loads(result_path.read_text(encoding="utf-8-sig")),
                    result_path,
                )
            else:
                results[key] = {
                    "fixture": fixture,
                    "corpus": corpus,
                    "population": "fresh_rebuild",
                    "pipeline_fingerprint": fingerprint,
                    "exit_state": "failed",
                    "error": f"worker exited {return_code} without a result",
                }
            print(f"{corpus}:{fixture} -> {results[key].get('exit_state')}", flush=True)
            checkpoint()

    after = {
        "job_files": {str(path): file_digest(path) for path in ACTIVE_JOB_FILES},
        "output_inventory": directory_inventory_digest(ACTIVE_OUTPUT_DIR),
    }
    isolation_passed = before == after
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest["completed"] = datetime.now().astimezone().isoformat()
    manifest["active_state_after"] = after
    manifest["active_state_unchanged"] = isolation_passed
    atomic_write_json(manifest_path, manifest)
    print(f"Manifest: {manifest_path}")
    print(f"Active state unchanged: {isolation_passed}")
    failures = [item for item in manifest["fixtures"] if item.get("exit_state") != "success"]
    return 0 if isolation_passed and not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
