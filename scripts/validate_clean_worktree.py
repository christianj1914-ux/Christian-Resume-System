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
    parser.add_argument("--commit", default="HEAD", help="Candidate commit or revision (default: HEAD).")
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
    try:
        candidate_sha = git_output("rev-parse", "--verify", f"{args.commit}^{{commit}}")
    except subprocess.CalledProcessError:
        print(f"Could not resolve candidate commit: {args.commit}")
        return 2

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
                print(f"CLEAN_VALIDATION commit={candidate_sha} untracked_dependencies=FAILED")
                print(status)
                return 1

            print(f"CLEAN_VALIDATION commit={candidate_sha} untracked_dependencies=0")
            environment = os.environ.copy()
            environment["PYTHONPYCACHEPREFIX"] = str(pycache)
            return_code, result = stream_validation(
                [sys.executable, "tasks.py", "validate-direct", *forwarded_args],
                cwd=worktree,
                env=environment,
            )
            if result is None:
                print(f"CLEAN_VALIDATION commit={candidate_sha} registered_checks=unknown result=FAILED")
                return 1 if return_code == 0 else return_code

            registered = int(result.group("registered"))
            passed = result.group("status") == "PASSED" and return_code == 0
            expected_matches = args.expected_count is None or registered == args.expected_count
            status_label = "PASS" if passed and expected_matches else "FAIL"
            print(
                f"CLEAN_VALIDATION commit={candidate_sha} registered_checks={registered} "
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
