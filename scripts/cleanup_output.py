#!/usr/bin/env python3
"""Prompt-driven cleanup for stale output files and render folders."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from tempfile import gettempdir
from typing import Iterable
import zipfile

import cleanup_render_checks
from config.paths import is_owner_owned_output, reject_owner_owned_output


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TRACKER_CSV = PROJECT_ROOT / "scratch" / "applications.csv"
RENDER_CHECK_PATTERN = "render_check"
RENDER_CHECK_MAX_DAYS = 7
OUTPUT_MAX_DAYS = 60
PROTECTED_STATUSES = {"interview", "phone_screen", "final_round", "offer", "rejected"}
RECENT_BUNDLE_DAYS = 14
BUNDLE_WINDOW_HOURS = 24
AUDIT_TOKEN_RE = re.compile(r"\s+(?:PASS|BRIDGE|FAIL|POOR)$")
ROUND_RE = re.compile(r"\s*\([^)]+\)$")
OUTPUT_PREFIX = "Christian Estrada - "
KNOWN_DOCUMENT_TYPES = (
    "Complete Interview Guide", "Round 2 Panel Interview Guide", "Detailed Interview Guide",
    "Team Round Prep Addendum", "Qualifications Statement", "Pre-Interview Checklist",
    "Application Checklist", "Interview Cheat Sheet", "90 Day Plan One-Pager", "Panel Master Guide",
    "Recruiter Screen Prep", "Thank You Note", "Thank-You Note", "LinkedIn Update",
    "Resume (Revised)", "Cover Letter", "Federal Resume", "Resume",
)
STANDALONE_PREFIXES = (
    "Christian Estrada - Career Operating Plan", "Christian Estrada - Daily Prep Plan",
    "Christian Estrada - Self-Inventory One-Pager", "Christian Estrada - Public Speaking Transformation Plan",
    "Christian Estrada - Interview Prep Kit", "Question_Bank_Audit_",
)
DEBUG_OUTPUT_PATTERNS = ("_stage_smoke*", "*_docbuild*", "sf_reg*")
DEBUG_OUTPUT_NAMES = {
    "State Farm Direct Regression Guide DRAFT.docx",
    "Sourcewell leakage check guide (HR Screen) DRAFT.docx",
}


def ask(prompt: str) -> bool:
    answer = input(prompt + " [Y/N]: ").strip().lower()
    return answer == "y"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selective", action="store_true")
    parser.add_argument("--remove-debug-artifacts", action="store_true")
    parser.add_argument("--prune-bundles", action="store_true")
    parser.add_argument("--prune-bundles-execute", action="store_true")
    return parser.parse_args(argv)


def normalize_company(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def age_in_days(path: Path) -> int:
    return max(0, (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days)


def company_name_from_output_file(path: Path) -> str:
    stem = path.stem
    prefix = "Christian Estrada - "
    remainder = stem[len(prefix):] if stem.startswith(prefix) else stem
    parts = [part.strip() for part in remainder.split(" - ") if part.strip()]
    company = parts[0] if parts else remainder
    company = company.replace(" FAIL", "").replace(" POOR", "").strip()
    company = company.removesuffix(" Long Cover Letter").removesuffix(" Cover Letter").removesuffix(" Resume").strip()
    return company


def protected_company_keys() -> set[str]:
    if not TRACKER_CSV.exists():
        return set()
    protected: set[str] = set()
    with TRACKER_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            status = (row.get("current_status") or "").strip().lower()
            if status not in PROTECTED_STATUSES:
                continue
            company = normalize_company(row.get("company", ""))
            if company:
                protected.add(company)
    return protected


def find_stale_render_folders() -> list[Path]:
    original_project_root = cleanup_render_checks.PROJECT_ROOT
    original_render_root = cleanup_render_checks.RENDER_ROOT
    try:
        cleanup_render_checks.PROJECT_ROOT = PROJECT_ROOT
        cleanup_render_checks.RENDER_ROOT = PROJECT_ROOT / "render_check"
        return cleanup_render_checks.old_render_folders(RENDER_CHECK_MAX_DAYS * 24)
    finally:
        cleanup_render_checks.PROJECT_ROOT = original_project_root
        cleanup_render_checks.RENDER_ROOT = original_render_root


def find_stale_output_files() -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    cutoff = datetime.now() - timedelta(days=OUTPUT_MAX_DAYS)
    protected = protected_company_keys()
    matches: list[Path] = []
    for path in sorted(OUTPUT_DIR.glob("*.docx")):
        if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
            continue
        company_key = normalize_company(company_name_from_output_file(path))
        if company_key and company_key in protected:
            continue
        matches.append(path)
    return matches


def delete_render_folder(folder: Path) -> None:
    if not cleanup_render_checks.is_safe_render_folder(folder):
        print(f"Skipped unsafe render folder target: {folder}")
        raise SystemExit(1)
    errors = cleanup_render_checks.remove_tree(folder)
    if errors:
        print("Some render folder files could not be removed:")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print(f"Deleted: {folder.name}")


def delete_output_file(path: Path) -> None:
    reject_owner_owned_output(path, "delete", OUTPUT_DIR)
    path.unlink()
    print(f"Deleted: {path.name}")


def cleanup_archive_dir() -> Path:
    return PROJECT_ROOT / "scratch" / "cleanup_archives"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_deletion_set(paths: Iterable[Path], reasons: dict[Path, str], label: str) -> tuple[Path, Path]:
    """Archive a planned output deletion and verify it before the caller unlinks anything."""
    candidates = sorted({path.resolve() for path in paths})
    for path in candidates:
        reject_owner_owned_output(path, f"archive for {label} cleanup", OUTPUT_DIR)
    if not candidates:
        raise ValueError("Cannot archive an empty deletion set.")
    archive_root = cleanup_archive_dir()
    archive_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zip_path = archive_root / f"output_cleanup_{label}_{stamp}.zip"
    manifest_path = zip_path.with_suffix(".json")
    entries: list[dict[str, object]] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in candidates:
            if not path.is_file():
                raise FileNotFoundError(f"Scheduled cleanup target disappeared: {path}")
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            entries.append({
                "path": relative,
                "size": path.stat().st_size,
                "sha256": _sha256(path),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                "reason": reasons[path],
            })
            archive.write(path, arcname=relative)
    with zipfile.ZipFile(zip_path) as archive:
        corrupt = archive.testzip()
        if corrupt is not None or len(archive.infolist()) != len(entries):
            zip_path.unlink(missing_ok=True)
            raise RuntimeError(f"Cleanup archive verification failed: {corrupt or 'entry-count mismatch'}")
    manifest_path.write_text(json.dumps({"archive": zip_path.name, "entries": entries}, indent=2) + "\n", encoding="utf-8")
    return zip_path, manifest_path


def _strip_once_for_family(value: str) -> tuple[str, bool]:
    changed = False
    if value.endswith(" DRAFT"):
        value = value[:-6].rstrip()
        changed = True
    round_match = ROUND_RE.search(value)
    if round_match and any(value[:round_match.start()].endswith(doc_type) for doc_type in KNOWN_DOCUMENT_TYPES):
        value = value[:round_match.start()].rstrip()
        changed = True
    for doc_type in KNOWN_DOCUMENT_TYPES:
        suffix = f" {doc_type}"
        if value.endswith(suffix):
            value = value[:-len(suffix)].rstrip()
            changed = True
            break
    audit_match = AUDIT_TOKEN_RE.search(value)
    if audit_match:
        value = value[:audit_match.start()].rstrip()
        changed = True
    return value, changed


def output_family_key(path: Path) -> str | None:
    """Return a conservative application-family key, or None for never-prune names."""
    stem = path.stem
    if stem.startswith(STANDALONE_PREFIXES) or not stem.startswith(OUTPUT_PREFIX):
        return None
    remainder = stem[len(OUTPUT_PREFIX):]
    if remainder.startswith("Interview Review - "):
        family = remainder[len("Interview Review - "):]
    else:
        family = remainder
        stripped_any = False
        while True:
            family, changed = _strip_once_for_family(family)
            stripped_any = stripped_any or changed
            if not changed:
                break
        if not stripped_any:
            return None
    family = re.sub(r"[^\w\s&-]", "", family.lower())
    family = re.sub(r"\s+", " ", family).strip().rstrip(" -").strip()
    return family or None


def output_document_type(path: Path) -> str | None:
    stem = path.stem
    for doc_type in KNOWN_DOCUMENT_TYPES:
        if re.search(rf"(?:^|\s){re.escape(doc_type)}(?:\s*\([^)]+\))?(?:\s+DRAFT)?$", stem):
            return doc_type
    return None


def bundle_cleanup_plan(paths: Iterable[Path] | None = None) -> tuple[dict[str, list[Path]], list[Path], list[Path]]:
    candidates = paths if paths is not None else OUTPUT_DIR.glob("*.docx")
    docx_paths = sorted(
        path
        for path in candidates
        if path.suffix.casefold() == ".docx" and not is_owner_owned_output(path, OUTPUT_DIR)
    )
    families: dict[str, list[Path]] = {}
    preserved: list[Path] = []
    for path in docx_paths:
        key = output_family_key(path)
        if key is None:
            preserved.append(path)
        else:
            families.setdefault(key, []).append(path)
    if not all(output_family_key(path) is not None or path in preserved for path in docx_paths):
        raise AssertionError("Every DOCX must produce a family key or an explicit None result.")
    if any(not key for key in families):
        raise AssertionError("Output family keys must not be empty.")
    family_count = len(families)
    if not 60 <= family_count <= 150:
        raise AssertionError(f"Output family count {family_count} is outside the safe 60-150 range.")

    protected = protected_company_keys()
    recent_cutoff = datetime.now() - timedelta(days=RECENT_BUNDLE_DAYS)
    removals: list[Path] = []
    for key, members in families.items():
        if len(members) < 3 or any(datetime.fromtimestamp(path.stat().st_mtime) >= recent_cutoff for path in members):
            preserved.extend(members)
            continue
        company_key = normalize_company(company_name_from_output_file(members[0]))
        if company_key in protected:
            preserved.extend(members)
            continue
        resumes = [path for path in members if output_document_type(path) in {"Resume", "Federal Resume"}]
        if not resumes:
            preserved.extend(members)
            continue
        newest_resume = max(resumes, key=lambda path: path.stat().st_mtime)
        keep_after = newest_resume.stat().st_mtime - timedelta(hours=BUNDLE_WINDOW_HOURS).total_seconds()
        for path in members:
            (preserved if path.stat().st_mtime >= keep_after else removals).append(path)
    return families, sorted(set(preserved)), sorted(set(removals))


def save_bundle_preview(families: dict[str, list[Path]], preserved: list[Path], removals: list[Path]) -> Path:
    cleanup_archive_dir().mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    preview_path = cleanup_archive_dir() / f"prune_preview_{stamp}.txt"
    retained = {path.resolve() for path in preserved}
    lines = [f"Family count: {len(families)}", f"Retained: {len(preserved)}", f"Scheduled removals: {len(removals)}", ""]
    for key, members in sorted(families.items()):
        lines.append(f"[{key}]")
        for path in sorted(members):
            action = "KEEP" if path.resolve() in retained else "REMOVE"
            lines.append(f"  {action} {path.name}")
    preview_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return preview_path


def remove_output_set(paths: list[Path], reason: str, label: str) -> tuple[Path, Path] | None:
    for path in paths:
        reject_owner_owned_output(path, f"include in {label} cleanup", OUTPUT_DIR)
    if not paths:
        print(f"No {label} files found.")
        return None
    reasons = {path.resolve(): reason for path in paths}
    archive_path, manifest_path = archive_deletion_set(paths, reasons, label)
    for path in paths:
        delete_output_file(path)
    print(f"Archived {len(paths)} file(s): {archive_path}")
    return archive_path, manifest_path


def debug_output_artifacts() -> list[Path]:
    candidates = {path for pattern in DEBUG_OUTPUT_PATTERNS for path in OUTPUT_DIR.glob(pattern)}
    candidates.update(OUTPUT_DIR / name for name in DEBUG_OUTPUT_NAMES if (OUTPUT_DIR / name).is_file())
    return sorted(
        path for path in candidates
        if path.is_file() and not is_owner_owned_output(path, OUTPUT_DIR)
    )


def remove_debug_artifacts() -> tuple[Path, Path] | None:
    return remove_output_set(debug_output_artifacts(), "non-application debug artifact", "debug_artifacts")


def run_cleanup(*, selective: bool = False) -> None:
    stale_render_folders = find_stale_render_folders()
    stale_output_files = find_stale_output_files()

    if not stale_render_folders and not stale_output_files:
        print("Nothing to clean up. All output files and render folders are within retention limits.")
        return

    if stale_render_folders:
        print(f"Found {len(stale_render_folders)} render check folder(s) older than {RENDER_CHECK_MAX_DAYS} days:")
        for folder in stale_render_folders:
            print(f"  {folder.name} ({age_in_days(folder)} days old)")
        deleted_any = False
        if selective:
            for folder in stale_render_folders:
                if ask(f"Delete {folder.name}?"):
                    delete_render_folder(folder)
                    deleted_any = True
            if not deleted_any:
                print("Skipped render check cleanup.")
        elif ask("Delete all stale render check folders?"):
            for folder in stale_render_folders:
                delete_render_folder(folder)
            deleted_any = True
        else:
            print("Skipped render check cleanup.")

    if stale_output_files:
        print(
            f"Found {len(stale_output_files)} output file(s) older than {OUTPUT_MAX_DAYS} days with no active interview process:"
        )
        for path in stale_output_files:
            print(f"  {path.name} ({age_in_days(path)} days old)")
        deleted_any = False
        if selective:
            for path in stale_output_files:
                if ask(f"Delete {path.name} ({age_in_days(path)} days old)?"):
                    delete_output_file(path)
                    deleted_any = True
            if not deleted_any:
                print("Skipped output file cleanup.")
        elif ask("Delete all stale output files?"):
            for path in stale_output_files:
                delete_output_file(path)
            deleted_any = True
        else:
            print("Skipped output file cleanup.")


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.prune_bundles_execute and not arguments.prune_bundles:
        raise SystemExit("--prune-bundles-execute requires --prune-bundles.")
    if arguments.remove_debug_artifacts:
        remove_debug_artifacts()
    if arguments.prune_bundles:
        families, preserved, removals = bundle_cleanup_plan()
        preview = save_bundle_preview(families, preserved, removals)
        print(f"Bundle pruning preview: {preview}")
        print(f"Families: {len(families)}; retained: {len(preserved)}; proposed removals: {len(removals)}")
        if arguments.prune_bundles_execute:
            remove_output_set(removals, "superseded application output bundle", "bundle_prune")
    if not any((arguments.remove_debug_artifacts, arguments.prune_bundles)):
        run_cleanup(selective=arguments.selective)
