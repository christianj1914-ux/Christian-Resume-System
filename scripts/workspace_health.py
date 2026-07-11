#!/usr/bin/env python3
"""Workspace preflight, git-state reporting, and targeted recovery helpers."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
QUESTION_PREP_PATH = SCRIPTS_DIR / "question_prep.py"
BACKUPS_DIR = PROJECT_ROOT / "backups"
QUESTION_CATEGORY_RECONSTRUCTION = PROJECT_ROOT / "Claude Review" / "question_category_reconstructed.py"
REQUIRED_QUESTION_PREP_SYMBOLS = (
    "question_category",
    "answer_prompt",
    "active_application_question_responses",
    "dedupe_question_responses",
    "interviewer_question_category",
    "recent_interviewer_question_prep_items",
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    import hashlib

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def completed_process_detail(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    return detail or f"exit code {result.returncode}"


def git_health(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    try:
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return {
            "status": "git-unavailable",
            "root": None,
            "head": None,
            "dirty": None,
            "detail": "git executable not found",
        }

    if toplevel.returncode != 0:
        dot_git = project_root / ".git"
        if dot_git.is_dir():
            try:
                has_entries = any(dot_git.iterdir())
            except OSError:
                has_entries = True
            status = "git-metadata-empty" if not has_entries else "not-a-git-repository"
        else:
            status = "not-a-git-repository"
        return {
            "status": status,
            "root": None,
            "head": None,
            "dirty": None,
            "detail": completed_process_detail(toplevel),
        }

    repo_root = Path(toplevel.stdout.strip())
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if head.returncode != 0:
        return {
            "status": "git-head-unavailable",
            "root": str(repo_root),
            "head": None,
            "dirty": None,
            "detail": completed_process_detail(head),
        }

    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "status": "healthy",
        "root": str(repo_root),
        "head": head.stdout.strip(),
        "dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
        "detail": "repository available",
    }


def load_module_from_path(source_path: Path) -> Any:
    module_name = f"_workspace_health_{source_path.stem}_{abs(hash(str(source_path.resolve())))}"
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create an import spec for {source_path}")
    module = importlib.util.module_from_spec(spec)
    inserted = False
    inserted_module = False
    scripts_dir = str(SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
        inserted = True
    try:
        if module_name not in sys.modules:
            sys.modules[module_name] = module
            inserted_module = True
        spec.loader.exec_module(module)
    finally:
        if inserted_module:
            sys.modules.pop(module_name, None)
        if inserted:
            sys.path.pop(0)
    return module


def question_prep_health(project_root: Path = PROJECT_ROOT, source_path: Path | None = None) -> dict[str, Any]:
    target = source_path or (project_root / "scripts" / "question_prep.py")
    result: dict[str, Any] = {
        "path": str(target.resolve()),
        "status": "healthy",
        "parse_ok": False,
        "import_ok": False,
        "required_symbols": list(REQUIRED_QUESTION_PREP_SYMBOLS),
        "missing_symbols": [],
        "detail": "",
    }

    if not target.exists():
        result["status"] = "missing"
        result["detail"] = f"Missing file: {target}"
        return result

    try:
        ast.parse(target.read_text(encoding="utf-8"))
        result["parse_ok"] = True
    except Exception as error:  # noqa: BLE001
        result["status"] = "parse-failed"
        result["detail"] = f"{type(error).__name__}: {error}"
        return result

    try:
        module = load_module_from_path(target)
        result["import_ok"] = True
    except Exception as error:  # noqa: BLE001
        result["status"] = "import-failed"
        result["detail"] = f"{type(error).__name__}: {error}"
        return result

    missing = [name for name in REQUIRED_QUESTION_PREP_SYMBOLS if not hasattr(module, name)]
    if missing:
        result["status"] = "surface-incomplete"
        result["missing_symbols"] = missing
        result["detail"] = "Missing required symbols: " + ", ".join(missing)
        return result

    result["detail"] = "question_prep.py parses and exposes all required symbols."
    return result


def backup_candidates(project_root: Path = PROJECT_ROOT) -> list[Path]:
    backups_root = project_root / "backups"
    if not backups_root.is_dir():
        return []
    return sorted(
        backups_root.rglob("question_prep.py"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def recovery_plan(project_root: Path = PROJECT_ROOT, git: dict[str, Any] | None = None) -> list[str]:
    git_state = git or git_health(project_root)
    steps: list[str] = []
    if git_state["status"] == "healthy":
        steps.append("Use `git restore -- scripts/question_prep.py` from this workspace root first.")
    elif (project_root / "backups").is_dir():
        steps.append("Git restore is unavailable here; use the newest acceptable `backups/**/question_prep.py` fallback that still passes parse plus six-symbol checks.")
    else:
        steps.append("Git restore is unavailable here and no `backups/` tree is available at this path.")
    if QUESTION_CATEGORY_RECONSTRUCTION.exists():
        steps.append("Do not use `Claude Review/question_category_reconstructed.py` as a whole-file substitute; use it only as partial reconstruction evidence.")
    return steps


def workspace_snapshot(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    git = git_health(project_root)
    question = question_prep_health(project_root)
    workspace_ok = question["status"] == "healthy"
    return {
        "project_root": str(project_root.resolve()),
        "generated_at": utc_timestamp(),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "git": git,
        "question_prep": question,
        "workspace_ok": workspace_ok,
        "workspace_state": "healthy" if workspace_ok else "needs-recovery",
        "recovery_plan": recovery_plan(project_root, git),
    }


def format_git_line(git: dict[str, Any]) -> str:
    if git["status"] == "healthy":
        dirty = "dirty" if git["dirty"] else "clean"
        head = (git["head"] or "")[:12]
        return f"Git: healthy at {git['root']} (HEAD {head}, {dirty})"
    return f"Git: {git['status']} ({git['detail']})"


def format_preflight_line(snapshot: dict[str, Any]) -> str:
    question = snapshot["question_prep"]
    if snapshot["workspace_ok"]:
        return "Preflight: PASS - question_prep.py parses and exposes all six required symbols."
    return f"Preflight: FAIL - {question['detail']}"


def format_banner(snapshot: dict[str, Any]) -> str:
    lines = [
        f"Workspace root: {snapshot['project_root']}",
        f"Python: {snapshot['python_executable']} ({snapshot['python_version']})",
        format_git_line(snapshot["git"]),
        format_preflight_line(snapshot),
    ]
    if not snapshot["workspace_ok"]:
        lines.extend(f"Recovery: {step}" for step in snapshot["recovery_plan"])
    return "\n".join(lines)


def attempt_question_prep_recovery(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    initial = workspace_snapshot(project_root)
    if initial["workspace_ok"]:
        return {"attempted": False, "recovered": False, "method": None, "snapshot": initial}

    target = project_root / "scripts" / "question_prep.py"
    git = initial["git"]
    if git["status"] == "healthy":
        restore = subprocess.run(
            ["git", "restore", "--", "scripts/question_prep.py"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if restore.returncode == 0:
            refreshed = workspace_snapshot(project_root)
            if refreshed["workspace_ok"]:
                return {
                    "attempted": True,
                    "recovered": True,
                    "method": "git-restore",
                    "snapshot": refreshed,
                }

    for candidate in backup_candidates(project_root):
        candidate_health = question_prep_health(project_root, candidate)
        if candidate_health["status"] != "healthy":
            continue
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preserved = target.with_name(f"question_prep.pre_recovery_{timestamp}.py")
        if target.exists():
            shutil.copy2(target, preserved)
        shutil.copy2(candidate, target)
        refreshed = workspace_snapshot(project_root)
        if refreshed["workspace_ok"]:
            return {
                "attempted": True,
                "recovered": True,
                "method": f"backup:{candidate}",
                "snapshot": refreshed,
            }

    return {"attempted": True, "recovered": False, "method": None, "snapshot": initial}


def ensure_workspace_health_or_exit(workflow_name: str, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    outcome = attempt_question_prep_recovery(project_root)
    snapshot = outcome["snapshot"]
    if snapshot["workspace_ok"]:
        if outcome["method"] == "git-restore":
            print("Workspace recovery: restored scripts/question_prep.py from Git before build steps.")
        elif outcome["method"] and str(outcome["method"]).startswith("backup:"):
            print(f"Workspace recovery: restored scripts/question_prep.py from {outcome['method'][7:]}.")
        else:
            print("Workspace preflight: PASS")
        return snapshot

    message_lines = [
        f"{workflow_name} stopped before build steps because workspace preflight failed.",
        format_preflight_line(snapshot),
        *[f"Recovery: {step}" for step in snapshot["recovery_plan"]],
    ]
    raise SystemExit("\n".join(message_lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report workspace health and targeted recovery guidance.")
    parser.add_argument("--json", action="store_true", help="Print the workspace snapshot as JSON.")
    parser.add_argument("--banner", action="store_true", help="Print a launcher-friendly text banner.")
    parser.add_argument("--require-healthy", action="store_true", help="Exit non-zero when the workspace is not healthy.")
    parser.add_argument("--attempt-recovery", action="store_true", help="Try the path-aware question_prep recovery order before reporting.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.attempt_recovery:
        snapshot = attempt_question_prep_recovery()["snapshot"]
    else:
        snapshot = workspace_snapshot()
    if args.json:
        print(json.dumps(snapshot, indent=2))
    else:
        print(format_banner(snapshot))
    if args.require_healthy and not snapshot["workspace_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
