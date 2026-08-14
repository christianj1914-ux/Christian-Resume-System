#!/usr/bin/env python3
"""Collect and verify the pinned CI renderer toolchain without short-circuiting."""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence, TextIO


EXPECTED_PACKAGES = {
    "libreoffice-fresh": "7.6.5",
    "poppler": "26.5.0",
}
LIBREOFFICE_VERSION_PATTERN = re.compile(r"LibreOffice 7\.6\.5\.2\b")
POPPLER_VERSION_PATTERN = re.compile(r"pdftoppm version 26\.05\.0\b")

ProbeResult = dict[str, object]
PackageQuery = Callable[[str], ProbeResult]
ResolverLoader = Callable[[], Mapping[str, Callable[[], object]]]
CommandRunner = Callable[[Sequence[str]], ProbeResult]


def _failure(error: BaseException) -> ProbeResult:
    return {
        "ok": False,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "error": f"{type(error).__name__}: {error}",
    }


def _run_command(command: Sequence[str]) -> ProbeResult:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        return _failure(error)
    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "error": "" if result.returncode == 0 else f"command exited {result.returncode}",
    }


def _query_chocolatey(package: str) -> ProbeResult:
    return _run_command(("choco", "list", "--exact", "--limit-output", package))


def _load_resolvers() -> Mapping[str, Callable[[], object]]:
    from render_docx_windows import find_pdftoppm, find_soffice

    return {"libreoffice": find_soffice, "poppler": find_pdftoppm}


def _probe_value(result: ProbeResult) -> str:
    return "\n".join(
        part for part in (str(result.get("stdout", "")), str(result.get("stderr", ""))) if part
    ).strip()


def collect_diagnostics(
    package_query: PackageQuery = _query_chocolatey,
    resolver_loader: ResolverLoader = _load_resolvers,
    command_runner: CommandRunner = _run_command,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Collect every independent observation, retaining failures instead of raising."""

    environment = dict(os.environ if environ is None else environ)
    report: dict[str, object] = {
        "schema_version": 1,
        "environment": {
            "github_actions": environment.get("GITHUB_ACTIONS", "").casefold() == "true",
            "path": environment.get("PATH", ""),
            "selected_poppler_directory": environment.get("RESUME_CI_POPPLER_DIR", ""),
        },
        "packages": {},
        "resolver_import": {"ok": True, "error": ""},
        "resolvers": {},
        "versions": {},
    }

    packages = report["packages"]
    assert isinstance(packages, dict)
    for package in EXPECTED_PACKAGES:
        try:
            packages[package] = package_query(package)
        except Exception as error:  # diagnostic boundary: retain and continue
            packages[package] = _failure(error)

    try:
        resolvers = resolver_loader()
    except Exception as error:  # imports are a separate diagnostic category
        report["resolver_import"] = {
            "ok": False,
            "category": "resolver_import_failure",
            "error": f"{type(error).__name__}: {error}",
        }
        resolvers = {}

    resolver_results = report["resolvers"]
    version_results = report["versions"]
    assert isinstance(resolver_results, dict)
    assert isinstance(version_results, dict)
    commands = {"libreoffice": "--version", "poppler": "-v"}
    for name in ("libreoffice", "poppler"):
        resolver = resolvers.get(name)
        if resolver is None:
            resolver_results[name] = {
                "ok": False,
                "path": "",
                "error": "resolver unavailable after import failure",
            }
            version_results[name] = {
                "ok": False,
                "skipped": True,
                "error": "version probe skipped because resolver was unavailable",
            }
            continue
        try:
            path = str(resolver())
            resolver_results[name] = {"ok": True, "path": path, "error": ""}
        except Exception as error:
            resolver_results[name] = {
                "ok": False,
                "path": "",
                "error": f"{type(error).__name__}: {error}",
            }
            version_results[name] = {
                "ok": False,
                "skipped": True,
                "error": "version probe skipped because resolver failed",
            }
            continue
        try:
            version_results[name] = command_runner((path, commands[name]))
        except Exception as error:
            version_results[name] = _failure(error)

    return report


def evaluate_diagnostics(report: Mapping[str, object]) -> list[str]:
    """Return all verification failures after collection has completed."""

    failures: list[str] = []
    packages = report.get("packages", {})
    if not isinstance(packages, Mapping):
        failures.append("package diagnostics are missing")
        packages = {}
    for package, expected in EXPECTED_PACKAGES.items():
        result = packages.get(package, {})
        if not isinstance(result, Mapping) or not result.get("ok"):
            detail = result.get("error", "missing result") if isinstance(result, Mapping) else "invalid result"
            failures.append(f"Chocolatey query failed for {package}: {detail}")
            continue
        lines = {line.strip().casefold() for line in _probe_value(dict(result)).splitlines() if line.strip()}
        expected_line = f"{package}|{expected}".casefold()
        if expected_line not in lines:
            failures.append(f"Unexpected Chocolatey package version for {package}: {_probe_value(dict(result))!r}")

    resolver_import = report.get("resolver_import", {})
    if not isinstance(resolver_import, Mapping) or not resolver_import.get("ok"):
        detail = resolver_import.get("error", "missing result") if isinstance(resolver_import, Mapping) else "invalid result"
        failures.append(f"Renderer resolver import failed: {detail}")

    resolvers = report.get("resolvers", {})
    versions = report.get("versions", {})
    if not isinstance(resolvers, Mapping):
        resolvers = {}
    if not isinstance(versions, Mapping):
        versions = {}
    for name in ("libreoffice", "poppler"):
        result = resolvers.get(name, {})
        if not isinstance(result, Mapping) or not result.get("ok"):
            detail = result.get("error", "missing result") if isinstance(result, Mapping) else "invalid result"
            failures.append(f"{name} resolver failed: {detail}")

    version_patterns = {
        "libreoffice": LIBREOFFICE_VERSION_PATTERN,
        "poppler": POPPLER_VERSION_PATTERN,
    }
    for name, pattern in version_patterns.items():
        result = versions.get(name, {})
        if not isinstance(result, Mapping) or not result.get("ok"):
            detail = result.get("error", "missing result") if isinstance(result, Mapping) else "invalid result"
            failures.append(f"{name} version probe failed: {detail}")
            continue
        observed = _probe_value(dict(result))
        if not pattern.search(observed):
            failures.append(f"Unexpected {name} version: {observed!r}")

    environment = report.get("environment", {})
    if isinstance(environment, Mapping) and environment.get("github_actions"):
        selected = str(environment.get("selected_poppler_directory", ""))
        poppler = resolvers.get("poppler", {})
        resolved = str(poppler.get("path", "")) if isinstance(poppler, Mapping) else ""
        if not selected:
            failures.append("CI Poppler directory was not exported")
        elif resolved and Path(selected).resolve() != Path(resolved).resolve().parent:
            failures.append(f"CI Poppler directory disagrees with resolver: selected={selected!r} resolved={resolved!r}")

    return failures


def _escape_annotation(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def emit_diagnostics(
    report: Mapping[str, object],
    failures: Sequence[str],
    environ: Mapping[str, str] | None = None,
    output: TextIO | None = None,
) -> None:
    """Emit full local diagnostics plus GitHub-specific summary and annotation."""

    environment = dict(os.environ if environ is None else environ)
    stream = sys.stdout if output is None else output
    payload = {"report": report, "failures": list(failures), "result": "FAIL" if failures else "PASS"}
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    print(rendered, file=stream)

    summary_path = environment.get("GITHUB_STEP_SUMMARY", "")
    if summary_path:
        try:
            with Path(summary_path).open("a", encoding="utf-8") as handle:
                handle.write("## Renderer pin diagnostics\n\n```json\n")
                handle.write(rendered)
                handle.write("\n```\n")
        except OSError as error:
            print(f"GitHub step summary unavailable: {type(error).__name__}: {error}", file=stream)

    if environment.get("GITHUB_ACTIONS", "").casefold() == "true" and failures:
        compact = json.dumps({"failures": list(failures), "report": report}, separators=(",", ":"), ensure_ascii=False)
        print(f"::error title=Renderer pin verification::{_escape_annotation(compact)}", file=stream)


def run_probe(
    package_query: PackageQuery = _query_chocolatey,
    resolver_loader: ResolverLoader = _load_resolvers,
    command_runner: CommandRunner = _run_command,
    environ: Mapping[str, str] | None = None,
    output: TextIO | None = None,
) -> int:
    """Collect, evaluate, and emit one probe with injectable local or CI context."""

    report = collect_diagnostics(package_query, resolver_loader, command_runner, environ)
    failures = evaluate_diagnostics(report)
    emit_diagnostics(report, failures, environ, output)
    return 1 if failures else 0


def main() -> int:
    return run_probe()


if __name__ == "__main__":
    raise SystemExit(main())
