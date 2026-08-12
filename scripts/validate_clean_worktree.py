"""Run the smoke suite from a temporary, detached clean Git worktree."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import _bootstrap  # type: ignore[import-not-found]

_bootstrap.ensure_script_path()
from resolve_python import resolve_python


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_PATTERN = re.compile(
    r"^Smoke test (?P<status>PASSED|FAILED): (?P<passed>\d+)/(?P<executed>\d+) "
    r"checks passed .*?\((?:[^;]*;\s*)?(?P<registered>\d+) total registered\)\."
)


def git_output(*arguments: str) -> str:
    """Return stdout from a Git command rooted at the canonical repository."""
    return subprocess.run(
        ("git", "-C", str(PROJECT_ROOT), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=(
            "Run validation from a temporary detached worktree so local edits, "
            "untracked files, and caches cannot affect the result."
        )
    )
    parser.add_argument(
        "--commit",
        help="Validate this exact commit or revision even when the developer workspace is dirty.",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        help="Fail unless the smoke suite reports this registered-check count.",
    )
    return parser.parse_known_args(argv)


def stream_validation(command: list[str], *, cwd: Path, env: dict[str, str]) -> tuple[int, re.Match[str] | None]:
    """Stream validation output while retaining its final registered-check result."""
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result: re.Match[str] | None = None
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        match = RESULT_PATTERN.match(line.strip())
        if match:
            result = match
    return process.wait(), result


def main(argv: list[str] | None = None) -> int:
    args, forwarded_args = parse_args(argv)
    explicit_commit = args.commit is not None
    if not explicit_commit:
        try:
            workspace_status = git_output("status", "--porcelain", "--untracked-files=all")
        except subprocess.CalledProcessError as error:
            print(f"Could not inspect the developer workspace: {error}")
            return 1
        if workspace_status:
            try:
                head_sha = git_output("rev-parse", "--verify", "HEAD^{commit}")
            except subprocess.CalledProcessError:
                head_sha = "unresolved"
            print(f"VALIDATION_REFUSED scope=workspace-default resolved_sha={head_sha} result=REFUSED")
            print("The developer workspace has changes that HEAD does not include:")
            print(workspace_status)
            print("Run 'python tasks.py validate-direct' to test the workspace before committing.")
            print("After committing, run 'python tasks.py validate', or select an artifact with '--commit <sha>'.")
            return 2

    requested_revision = args.commit or "HEAD"
    scope = "explicit-commit" if explicit_commit else "clean-head"
    try:
        candidate_sha = git_output("rev-parse", "--verify", f"{requested_revision}^{{commit}}")
    except subprocess.CalledProcessError:
        print(f"Could not resolve candidate commit: {requested_revision}")
        return 2

    print(f"VALIDATION_REQUEST scope={scope} resolved_sha={candidate_sha}")

    with tempfile.TemporaryDirectory(prefix="resume-system-clean-") as temporary_root:
        worktree = Path(temporary_root) / "candidate"
        pycache = Path(temporary_root) / "pycache"
        created = False
        try:
            subprocess.run(
                ("git", "-C", str(PROJECT_ROOT), "worktree", "add", "--detach", str(worktree), candidate_sha),
                check=True,
            )
            created = True
            status = subprocess.run(
                ("git", "-C", str(worktree), "status", "--porcelain", "--untracked-files=all"),
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if status:
                print(
                    f"CLEAN_VALIDATION resolved_sha={candidate_sha} scope={scope} "
                    "registered_checks=unknown executed_checks=unknown result=FAILED"
                )
                print(status)
                return 1

            print(f"CLEAN_VALIDATION commit={candidate_sha} untracked_dependencies=0")
            environment = os.environ.copy()
            environment["PYTHONPYCACHEPREFIX"] = str(pycache)
            return_code, result = stream_validation(
                [str(resolve_python(worktree) or sys.executable), "tasks.py", "validate-direct", *forwarded_args],
                cwd=worktree,
                env=environment,
            )
            if result is None:
                print(
                    f"CLEAN_VALIDATION resolved_sha={candidate_sha} scope={scope} "
                    "registered_checks=unknown executed_checks=unknown result=FAILED"
                )
                return 1 if return_code == 0 else return_code

            registered = int(result.group("registered"))
            executed = int(result.group("executed"))
            passed = result.group("status") == "PASSED" and return_code == 0
            expected_matches = args.expected_count is None or registered == args.expected_count
            status_label = "PASS" if passed and expected_matches else "FAIL"
            print(
                f"CLEAN_VALIDATION resolved_sha={candidate_sha} scope={scope} "
                f"registered_checks={registered} executed_checks={executed} "
                f"result={status_label}"
            )
            if not expected_matches:
                print(f"Expected {args.expected_count} registered checks; found {registered}.")
            return 0 if passed and expected_matches else 1
        finally:
            if created:
                subprocess.run(
                    ("git", "-C", str(PROJECT_ROOT), "worktree", "remove", "--force", str(worktree)),
                    check=False,
                )


if __name__ == "__main__":
    raise SystemExit(main())
