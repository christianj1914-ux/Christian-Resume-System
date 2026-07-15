#!/usr/bin/env python3
"""Bootstrap the canonical local repo and retire the OneDrive launchers after validation."""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANONICAL_ROOT = Path(r"C:\dev\Christian-Resume-System")
SAFE_RESET_ROOT = Path(r"C:\dev")
DEFAULT_BRANCH = "main"
PYTHON = sys.executable
ROOT_EXCLUDED_FILES = {"err.txt", "err_c", "err_tmp", "err_pc"}
ROOT_EXCLUDED_GLOBS = ("debug-*.log",)
ROOT_COPY_EXCLUDED_FILES = {"DO_NOT_RUN_FROM_ONEDRIVE.txt"}
ROOT_COPY_EXCLUDED_GLOBS = ("run_*.bat",)
EXCLUDED_DIR_NAMES = {".git", "output", "backup", "backups", ".tmp", "tmp", "__pycache__"}
EXCLUDED_DIR_PREFIXES = ("render_check", "review_updated_sources")
ALLOWED_SCRATCH_FILES = {"scratch/applications.csv"}
ALLOWED_SCRATCH_PREFIXES = ("scratch/jd_library/", "scratch/target_jds/")
BOOTSTRAP_GITIGNORE = """output/
render_check*/
review_updated_sources*/
backup/
backups/
.tmp/
tmp/
__pycache__/
*.py[cod]
/err.txt
/err_c
/err_tmp
/debug-*.log
Claude Review/TEMP_*
Claude Review/BUNDLE_MANIFEST.json
Claude Review/history/
scratch/*
!scratch/
!scratch/applications.csv
!scratch/jd_library/
!scratch/jd_library/**
!scratch/target_jds/
!scratch/target_jds/**
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the canonical local repo in C:\\dev and retire the OneDrive launchers.")
    parser.add_argument("--source-root", type=Path, default=PROJECT_ROOT, help="Current healthy source workspace.")
    parser.add_argument("--canonical-root", type=Path, default=DEFAULT_CANONICAL_ROOT, help="Destination for the new canonical repo.")
    parser.add_argument("--git-name", default="", help="Optional git user.name to set locally before the initial commit.")
    parser.add_argument("--git-email", default="", help="Optional git user.email to set locally before the initial commit.")
    parser.add_argument("--remote-url", default="", help="Optional private remote URL to add as origin and push after bootstrap.")
    parser.add_argument("--skip-remote-push", action="store_true", help="Skip the remote add/push step even when --remote-url is provided.")
    parser.add_argument("--reset-destination", action="store_true", help="Delete an incomplete destination folder before copying.")
    return parser.parse_args()


def run_command(command: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{' '.join(command)} failed in {cwd}: {detail}")
    return result


def print_step(message: str) -> None:
    print(f"\n==> {message}")


def rel_text(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def is_root_excluded_file(rel_path: Path) -> bool:
    if len(rel_path.parts) != 1:
        return False
    if rel_path.name in ROOT_EXCLUDED_FILES:
        return True
    return any(fnmatch.fnmatch(rel_path.name, pattern) for pattern in ROOT_EXCLUDED_GLOBS)


def is_root_copy_excluded_file(rel_path: Path) -> bool:
    if len(rel_path.parts) != 1:
        return False
    if is_root_excluded_file(rel_path):
        return True
    if rel_path.name in ROOT_COPY_EXCLUDED_FILES:
        return True
    return any(fnmatch.fnmatch(rel_path.name, pattern) for pattern in ROOT_COPY_EXCLUDED_GLOBS)


def scratch_path_allowed(rel_path: Path) -> bool:
    rel = rel_path.as_posix()
    if rel == "scratch":
        return True
    if rel in ALLOWED_SCRATCH_FILES:
        return True
    if rel in {"scratch/jd_library", "scratch/target_jds"}:
        return True
    return any(rel.startswith(prefix) for prefix in ALLOWED_SCRATCH_PREFIXES)


def should_exclude(rel_path: Path, *, is_dir: bool) -> bool:
    if not rel_path.parts:
        return False
    rel = rel_path.as_posix()
    if rel_path.parts[0] == "scratch":
        return not scratch_path_allowed(rel_path)
    if any(part in EXCLUDED_DIR_NAMES for part in rel_path.parts):
        return True
    if is_dir and any(part.startswith(prefix) for part in rel_path.parts for prefix in EXCLUDED_DIR_PREFIXES):
        return True
    if rel.startswith("Claude Review/") and rel_path.name.startswith("TEMP_"):
        return True
    if is_root_copy_excluded_file(rel_path):
        return True
    return False


def git_head_exists(repo_root: Path) -> bool:
    result = run_command(["git", "rev-parse", "HEAD"], cwd=repo_root, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def destination_state(destination: Path) -> str:
    if not destination.exists():
        return "missing"
    if not any(destination.iterdir()):
        return "empty"
    if (destination / ".git").exists():
        return "git-with-commit" if git_head_exists(destination) else "git-without-commit"
    return "populated-non-git"


def can_safely_reset(destination: Path) -> bool:
    resolved = destination.resolve()
    safe_root = SAFE_RESET_ROOT.resolve()
    try:
        resolved.relative_to(safe_root)
    except ValueError:
        return False
    return len(resolved.parts) > len(safe_root.parts)


def make_writable(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass


def remove_tree_force(root: Path) -> None:
    for current_root, dirnames, filenames in os.walk(root, topdown=False):
        current_dir = Path(current_root)
        for filename in filenames:
            file_path = current_dir / filename
            make_writable(file_path)
            try:
                file_path.unlink()
            except OSError as error:
                raise RuntimeError(f"Could not remove file while resetting destination: {file_path} ({error})") from error
        for dirname in dirnames:
            dir_path = current_dir / dirname
            make_writable(dir_path)
            try:
                if dir_path.is_symlink():
                    dir_path.unlink()
                else:
                    dir_path.rmdir()
            except OSError as error:
                raise RuntimeError(f"Could not remove directory while resetting destination: {dir_path} ({error})") from error
    make_writable(root)
    try:
        root.rmdir()
    except OSError as error:
        raise RuntimeError(f"Could not remove destination root while resetting: {root} ({error})") from error


def prepare_destination(destination: Path, *, reset_destination: bool) -> None:
    state = destination_state(destination)
    if state == "missing":
        destination.mkdir(parents=True, exist_ok=False)
        return
    if state == "empty":
        return
    if reset_destination:
        if not can_safely_reset(destination):
            raise RuntimeError(f"Refusing to reset an unsafe destination path: {destination}")
        remove_tree_force(destination)
        destination.mkdir(parents=True, exist_ok=False)
        return
    if state in {"git-without-commit", "populated-non-git"}:
        raise RuntimeError(
            f"Destination already exists in an incomplete state: {destination}. "
            "Rerun with --reset-destination or remove that folder first."
        )
    raise RuntimeError(
        f"Destination already contains a committed repo: {destination}. "
        "Choose a different canonical path or remove/archive the existing repo first."
    )


def copy_workspace(source_root: Path, destination_root: Path) -> None:
    print_step(f"Copying workspace to {destination_root}")
    prepare_destination(destination_root, reset_destination=False)
    for current_root, dirnames, filenames in os_walk(source_root):
        current_path = Path(current_root)
        rel_dir = current_path.relative_to(source_root)
        dest_dir = destination_root / rel_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        kept_dirs: list[str] = []
        for dirname in dirnames:
            rel_child = rel_dir / dirname
            if should_exclude(rel_child, is_dir=True):
                continue
            kept_dirs.append(dirname)
            (destination_root / rel_child).mkdir(parents=True, exist_ok=True)
        dirnames[:] = kept_dirs

        for filename in filenames:
            rel_file = rel_dir / filename
            if should_exclude(rel_file, is_dir=False):
                continue
            destination_path = destination_root / rel_file
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_root / rel_file, destination_path)


def os_walk(root: Path):
    import os

    return os.walk(root)


def write_bootstrap_gitignore(destination_root: Path) -> None:
    print_step("Writing bootstrap .gitignore")
    (destination_root / ".gitignore").write_text(BOOTSTRAP_GITIGNORE, encoding="utf-8")


def batch_text(lines: list[str]) -> str:
    return "\r\n".join(lines) + "\r\n"


def canonical_launcher_text(body_lines: list[str]) -> str:
    lines = [
        "@echo off",
        "setlocal",
        'cd /d "%~dp0"',
        "",
        "call :resolve_python || goto :failed",
        'echo Workspace root: %CD%',
        'echo Python: %RESOLVED_PYTHON%',
        '"%RESOLVED_PYTHON%" ".\\scripts\\workspace_health.py" --banner --require-healthy',
        "if errorlevel 1 goto :failed",
        "",
        *body_lines,
        "",
        ":done",
        "echo.",
        "pause",
        "exit /b 0",
        "",
        ":failed",
        "echo.",
        "echo The launcher stopped before continuing.",
        "pause",
        "exit /b 1",
        "",
        ":resolve_python",
        'if defined RESUME_PYTHON if exist "%RESUME_PYTHON%" set "RESOLVED_PYTHON=%RESUME_PYTHON%"',
        'if not defined RESOLVED_PYTHON if exist "%USERPROFILE%\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" set "RESOLVED_PYTHON=%USERPROFILE%\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe"',
        'if not defined RESOLVED_PYTHON for /f "delims=" %%P in (\'where python 2^>nul\') do if not defined RESOLVED_PYTHON set "RESOLVED_PYTHON=%%P"',
        "if not defined RESOLVED_PYTHON (",
        "  echo ERROR: No usable Python executable found. Set RESUME_PYTHON or install Python 3.11+.",
        "  exit /b 1",
        ")",
        "exit /b 0",
        "",
        ":run_task",
        "echo.",
        "echo Running: python tasks.py %*",
        '"%RESOLVED_PYTHON%" ".\\tasks.py" %*',
        "exit /b %ERRORLEVEL%",
    ]
    return batch_text(lines)


def canonical_bootstrap_launcher_text() -> str:
    return batch_text(
        [
            "@echo off",
            "setlocal",
            'cd /d "%~dp0"',
            "echo This repo is already the canonical repo.",
            "echo To bootstrap a new canonical repo from another source workspace, run scripts\\bootstrap_canonical_repo.py with an explicit --source-root and --canonical-root.",
            "pause",
            "exit /b 0",
        ]
    )


def write_canonical_launchers(destination_root: Path) -> None:
    print_step("Writing canonical launchers")
    launchers = {
        "run_resume.bat": canonical_launcher_text(
            [
                'if not exist ".\\output" mkdir ".\\output"',
                "",
                "echo.",
                "echo Choose what to build:",
                "echo   [R] Resume only",
                "echo   [F] Full workflow (resume + cover letter + qualifications)",
                "echo   [D] Dry run only",
                "echo.",
                'choice /c RFD /n /m "Selection [R/F/D]: "',
                "if errorlevel 3 goto :run_dry",
                "if errorlevel 2 goto :run_full",
                "call :run_task resume --resume-only",
                "if errorlevel 1 goto :failed",
                "goto :done",
                "",
                ":run_dry",
                "call :run_task dry-run || goto :failed",
                "goto :done",
                "",
                ":run_full",
                "call :run_task resume",
                "if errorlevel 2 goto :draft_cover_letter",
                "if errorlevel 1 goto :failed",
                "goto :done",
                "",
                ":draft_cover_letter",
                "echo.",
                "echo Resume created, but the cover letter was saved as DRAFT.",
                "echo Qualifications and later steps were skipped by design.",
                "goto :done",
            ]
        ),
        "run_federal_resume.bat": canonical_launcher_text(
            [
                'if not exist ".\\output" mkdir ".\\output"',
                "",
                "echo.",
                'choice /c YN /n /m "Run a dry run instead of creating documents? [Y/N] "',
                "if errorlevel 2 goto :run_live",
                "call :run_task federal-dry-run || goto :failed",
                "goto :done",
                "",
                ":run_live",
                "call :run_task federal-resume || goto :failed",
                "goto :done",
            ]
        ),
        "run_claude_refresh.bat": canonical_launcher_text(
            [
                "echo.",
                'choice /c YN /n /m "Skip checks for a faster Claude refresh? [Y/N] "',
                "if errorlevel 2 goto :run_full",
                "call :run_task claude-refresh --skip-checks || goto :failed",
                "goto :done",
                "",
                ":run_full",
                "call :run_task claude-refresh || goto :failed",
                "goto :done",
            ]
        ),
        "run_detailed_interview_guide.bat": canonical_launcher_text(
            [
                'if not exist ".\\output" mkdir ".\\output"',
                "",
                "echo.",
                "echo This builds the interview cheat sheet and the detailed commercial interview guide.",
                'choice /c YN /n /m "Continue? [Y/N] "',
                "if errorlevel 2 goto :done",
                "echo.",
                "echo Choose the interview stage for the detailed guide:",
                "echo   [1] HR",
                "echo   [2] Hiring Mgr",
                "echo   [3] Panel",
                "echo   [4] Presentation",
                "echo   [5] Technical",
                "echo   [6] Final",
                "echo   [7] All",
                'choice /c 1234567 /n /m "Selection [1-7]: "',
                'set "GUIDE_STAGE=hr_screen"',
                'if errorlevel 7 set "GUIDE_STAGE=all"',
                'if errorlevel 6 set "GUIDE_STAGE=final"',
                'if errorlevel 5 set "GUIDE_STAGE=technical"',
                'if errorlevel 4 set "GUIDE_STAGE=presentation"',
                'if errorlevel 3 set "GUIDE_STAGE=panel"',
                'if errorlevel 2 set "GUIDE_STAGE=hiring_manager"',
                "call :run_task interview || goto :failed",
                "call :run_task guide --stage %GUIDE_STAGE% || goto :failed",
                "call :offer_companions || goto :failed",
                "goto :done",
                "",
                ":offer_companions",
                'if /I "%GUIDE_STAGE%"=="hr_screen" call :offer_companion recruiter_screen "Also build the Recruiter Screen Prep companion? [Y/N] " || exit /b 1',
                'if /I "%GUIDE_STAGE%"=="hiring_manager" call :offer_companion first_90_days "Also build the 90 Day One-Pager companion? [Y/N] " || exit /b 1',
                "call :check_companion debrief_addendum",
                "if errorlevel 1 exit /b 0",
                'call :offer_companion debrief_addendum "Also build the Debrief Prep Addendum companion? [Y/N] " || exit /b 1',
                "exit /b 0",
                "",
                ":offer_companion",
                'set "COMPANION_MODE=%~1"',
                'set "COMPANION_PROMPT=%~2"',
                "echo.",
                'choice /c YN /n /m "%COMPANION_PROMPT%"',
                "if errorlevel 2 exit /b 0",
                "call :run_companion %COMPANION_MODE%",
                "exit /b %ERRORLEVEL%",
                "",
                ":check_companion",
                '"%RESOLVED_PYTHON%" ".\\scripts\\build_interview_companions.py" --mode %1 --check >nul 2>nul',
                "exit /b %ERRORLEVEL%",
                "",
                ":run_companion",
                "echo.",
                "echo Running: python scripts\\build_interview_companions.py --mode %*",
                '"%RESOLVED_PYTHON%" ".\\scripts\\build_interview_companions.py" --mode %*',
                "exit /b %ERRORLEVEL%",
            ]
        ),
        "run_post_interview_debrief.bat": canonical_launcher_text(
            [
                'set "RAN_ANY="',
                "echo.",
                "echo Choose either step, both steps, or skip both.",
                "echo - Prepare company notes opens or refreshes the company dossier scaffold.",
                "echo - Debrief captures fresh interview details after a conversation.",
                "echo.",
                'choice /c YN /n /m "Prepare company notes first? [Y/N] "',
                "if errorlevel 2 goto :skip_notes",
                "call :run_task prepare-company-notes || goto :failed",
                'set "RAN_ANY=1"',
                "",
                ":skip_notes",
                'choice /c YN /n /m "Capture a post-interview debrief now? [Y/N] "',
                "if errorlevel 2 goto :after_debrief",
                "call :run_task debrief || goto :failed",
                'set "RAN_ANY=1"',
                "",
                ":after_debrief",
                "if defined RAN_ANY goto :done",
                "echo.",
                "echo No step selected.",
                "goto :done",
            ]
        ),
        "run_cleanup.bat": canonical_launcher_text(
            [
                "echo.",
                'choice /c YN /n /m "Run cleanup now? [Y/N] "',
                "if errorlevel 2 goto :done",
                "call :run_task cleanup || goto :failed",
                "goto :done",
            ]
        ),
        "run_canonical_bootstrap.bat": canonical_bootstrap_launcher_text(),
    }
    for name, contents in launchers.items():
        (destination_root / name).write_text(contents, encoding="utf-8")


def ensure_git_identity(repo_root: Path, args: argparse.Namespace) -> None:
    if args.git_name:
        run_command(["git", "config", "user.name", args.git_name], cwd=repo_root)
    if args.git_email:
        run_command(["git", "config", "user.email", args.git_email], cwd=repo_root)
    name = run_command(["git", "config", "--get", "user.name"], cwd=repo_root, check=False).stdout.strip()
    email = run_command(["git", "config", "--get", "user.email"], cwd=repo_root, check=False).stdout.strip()
    if not name or not email:
        raise RuntimeError(
            "Git user.name and user.email are not configured. Set them globally or rerun with "
            "--git-name and --git-email. Example: --git-name \"Christian Estrada\" --git-email \"you@example.com\""
        )


def git_init_and_commit(repo_root: Path, args: argparse.Namespace) -> None:
    print_step("Initializing git")
    run_command(["git", "init"], cwd=repo_root)
    run_command(["git", "branch", "-M", DEFAULT_BRANCH], cwd=repo_root)
    ensure_git_identity(repo_root, args)
    run_command(["git", "add", "."], cwd=repo_root)
    run_command(["git", "commit", "-m", "Initial canonical repo bootstrap"], cwd=repo_root)


def verify_tracked_scratch(repo_root: Path) -> None:
    tracked = run_command(["git", "ls-files", "scratch"], cwd=repo_root).stdout.splitlines()
    bad = [
        path for path in tracked
        if path != "scratch/applications.csv"
        and not path.startswith("scratch/jd_library/")
        and not path.startswith("scratch/target_jds/")
    ]
    if bad:
        raise RuntimeError(f"Unexpected scratch paths are tracked: {bad}")
    if "scratch/applications.csv" not in tracked:
        raise RuntimeError("scratch/applications.csv is not tracked after bootstrap.")


def verify_clean_git_status(repo_root: Path) -> None:
    status = run_command(["git", "status", "--porcelain"], cwd=repo_root).stdout.strip()
    if status:
        raise RuntimeError(f"Canonical repo is not clean after bootstrap:\n{status}")


def validate_source_workspace(source_root: Path) -> None:
    print_step("Validating source workspace")
    checks = (
        [PYTHON, "-c", "import ast, pathlib; ast.parse(pathlib.Path('scripts/question_prep.py').read_text(encoding='utf-8'))"],
        [PYTHON, "-c", "import sys; sys.path.insert(0,'scripts'); import question_prep; [getattr(question_prep,n) for n in ['question_category','answer_prompt','active_application_question_responses','dedupe_question_responses','interviewer_question_category','recent_interviewer_question_prep_items']]"],
        [PYTHON, "tasks.py", "validate"],
        [PYTHON, "tasks.py", "federal-dry-run"],
    )
    for command in checks:
        run_command(command, cwd=source_root)


def validate_canonical_workspace(repo_root: Path) -> None:
    print_step("Validating canonical workspace")
    checks = (
        ["git", "rev-parse", "--show-toplevel"],
        ["git", "rev-parse", "HEAD"],
        [PYTHON, "tasks.py", "validate"],
        [PYTHON, "tasks.py", "integration-test"],
        [PYTHON, "tasks.py", "claude-refresh", "--skip-checks"],
        [PYTHON, "tasks.py", "claude-prompt", "plan", "--packet-mode", "federal"],
    )
    for command in checks:
        run_command(command, cwd=repo_root)
    verify_tracked_scratch(repo_root)
    verify_clean_git_status(repo_root)


def launcher_stub_text(canonical_root: Path) -> str:
    return (
        "@echo off\r\n"
        "echo This OneDrive copy is retired and archival only.\r\n"
        f"echo Canonical repo: {canonical_root}\r\n"
        "echo Run the matching launcher from the canonical repo instead.\r\n"
        "pause\r\n"
        "exit /b 1\r\n"
    )


def retire_source_launchers(source_root: Path, canonical_root: Path) -> None:
    print_step("Retiring OneDrive launchers")
    stub = launcher_stub_text(canonical_root)
    for launcher in source_root.rglob("*.bat"):
        if path_is_within(launcher, canonical_root):
            continue
        launcher.write_text(stub, encoding="utf-8")
    sentinel = source_root / "DO_NOT_RUN_FROM_ONEDRIVE.txt"
    sentinel.write_text(
        "\n".join(
            [
                "This OneDrive workspace is retired and archival only.",
                f"Canonical repo: {canonical_root}",
                "Re-select the Cowork folder to the canonical repo.",
                "Repoint Codex to the canonical repo.",
                "Repoint or recreate the codex-impl-progress-check task against the canonical repo.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def archive_cleanup_artifacts(source_root: Path) -> None:
    print_step("Archiving root error and debug artifacts")
    targets = [source_root / name for name in ROOT_EXCLUDED_FILES if (source_root / name).exists()]
    targets.extend(path for path in source_root.glob("debug-*.log") if path.is_file())
    if not targets:
        return
    archive_root = source_root / "Claude Review" / "history" / f"cleanup_artifacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    archive_root.mkdir(parents=True, exist_ok=False)
    for target in targets:
        shutil.move(str(target), str(archive_root / target.name))


def configure_remote(repo_root: Path, args: argparse.Namespace) -> None:
    if not args.remote_url or args.skip_remote_push:
        print("Remote push skipped. Add a private off-machine remote as the next step.")
        return
    print_step("Configuring private remote")
    run_command(["git", "remote", "add", "origin", args.remote_url], cwd=repo_root)
    run_command(["git", "push", "-u", "origin", DEFAULT_BRANCH], cwd=repo_root)


def main() -> int:
    try:
        args = parse_args()
        source_root = args.source_root.resolve()
        canonical_root = args.canonical_root.resolve()
        if source_root == canonical_root:
            raise RuntimeError("Source root and canonical root must be different paths.")

        validate_source_workspace(source_root)
        prepare_destination(canonical_root, reset_destination=args.reset_destination)
        copy_workspace(source_root, canonical_root)
        write_bootstrap_gitignore(canonical_root)
        write_canonical_launchers(canonical_root)
        git_init_and_commit(canonical_root, args)
        validate_canonical_workspace(canonical_root)
        retire_source_launchers(source_root, canonical_root)
        archive_cleanup_artifacts(source_root)
        configure_remote(canonical_root, args)

        print("\nCutover complete.")
        print(f"Canonical repo: {canonical_root}")
        print("Manual follow-up still required:")
        print(f"- Re-select Cowork to {canonical_root}")
        print(f"- Repoint Codex to {canonical_root}")
        print(f"- Repoint the codex-impl-progress-check task to {canonical_root}")
        return 0
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
