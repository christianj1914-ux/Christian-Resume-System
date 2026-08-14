#!/usr/bin/env python3
"""Collect and verify the pinned CI renderer toolchain without short-circuiting."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_MANIFEST = PROJECT_ROOT / "evals" / "equivalence" / "a14fb43" / "manifest.json"
EXPECTED_CHOCOLATEY_PACKAGES = {"libreoffice-fresh": "7.6.5"}
EXPECTED_CONDA_PACKAGE = "poppler"
EXPECTED_CONDA_BUILD = "h4b9d284_3"
LIBREOFFICE_PROBE_TIMEOUT_SECONDS = 15.0
POPPLER_PROBE_TIMEOUT_SECONDS = 30.0
PACKAGE_QUERY_TIMEOUT_SECONDS = 30.0

ProbeResult = dict[str, object]
ChocolateyQuery = Callable[[str], ProbeResult]
CondaQuery = Callable[[str, str], ProbeResult]
BaselineLoader = Callable[[], ProbeResult]
ResolverLoader = Callable[[], Mapping[str, Callable[[], object]]]
CommandRunner = Callable[[Sequence[str], float], ProbeResult]


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _failure(error: BaseException, *, category: str = "probe_failure") -> ProbeResult:
    return {
        "ok": False,
        "category": category,
        "exit_code": None,
        "stdout": _as_text(getattr(error, "stdout", "")),
        "stderr": _as_text(getattr(error, "stderr", "")),
        "error": f"{type(error).__name__}: {error}",
    }


def _run_command(command: Sequence[str], timeout_seconds: float) -> ProbeResult:
    """Run one probe while preserving the raw streams needed for production parity."""

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        return _failure(error, category="probe_timeout")
    except (OSError, subprocess.SubprocessError) as error:
        return _failure(error)
    return {
        "ok": result.returncode == 0,
        "category": "",
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": "" if result.returncode == 0 else f"command exited {result.returncode}",
    }


def _query_chocolatey(package: str) -> ProbeResult:
    return _run_command(
        ("choco", "list", "--exact", "--limit-output", package),
        PACKAGE_QUERY_TIMEOUT_SECONDS,
    )


def _query_conda(conda_root: str, prefix: str) -> ProbeResult:
    conda = Path(conda_root) / "Scripts" / "conda.exe"
    return _run_command(
        (str(conda), "list", "--prefix", prefix, "--json", EXPECTED_CONDA_PACKAGE),
        PACKAGE_QUERY_TIMEOUT_SECONDS,
    )


def _load_baseline_expectations() -> ProbeResult:
    try:
        payload = json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))
        values: dict[str, str] = {}
        for manifest_key, tool_name in (
            ("renderer_versions", "libreoffice"),
            ("poppler_versions", "poppler"),
        ):
            candidates = payload.get(manifest_key)
            if (
                not isinstance(candidates, list)
                or len(candidates) != 1
                or not isinstance(candidates[0], str)
                or not candidates[0].strip()
            ):
                raise ValueError(f"{manifest_key} must contain exactly one nonempty string")
            values[tool_name] = candidates[0]
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        result = _failure(error, category="baseline_expectation_failure")
        result["path"] = str(BASELINE_MANIFEST)
        return result
    return {
        "ok": True,
        "category": "",
        "path": str(BASELINE_MANIFEST),
        "values": values,
        "error": "",
    }


def _load_resolvers() -> Mapping[str, Callable[[], object]]:
    from render_docx_windows import find_pdftoppm, find_soffice

    return {"libreoffice": find_soffice, "poppler": find_pdftoppm}


def _probe_value(result: Mapping[str, object]) -> str:
    return "\n".join(
        part
        for part in (_as_text(result.get("stdout")), _as_text(result.get("stderr")))
        if part
    ).strip()


def _analyze_version_result(name: str, result: Mapping[str, object]) -> ProbeResult:
    analyzed = dict(result)
    stdout = _as_text(analyzed.get("stdout"))
    stderr = _as_text(analyzed.get("stderr"))
    analyzed["stdout"] = stdout
    analyzed["stderr"] = stderr
    analyzed["stdout_has_non_whitespace"] = bool(stdout.strip())
    analyzed["stderr_has_non_whitespace"] = bool(stderr.strip())

    if name == "libreoffice":
        # Deliberately mirror render_docx_windows.py. renderer_version is a
        # compared field, so whitespace-aware or combined-stream selection here
        # would let CI pass when production would record None.
        selected_raw = stdout if stdout else stderr
        analyzed["selected_stream"] = "stdout" if stdout else ("stderr" if stderr else "none")
        analyzed["production_renderer_version"] = selected_raw.strip() or None
        return analyzed

    if stdout.strip():
        selected_raw = stdout
        selected_stream = "stdout"
    elif stderr.strip():
        selected_raw = stderr
        selected_stream = "stderr"
    else:
        selected_raw = ""
        selected_stream = "none"
    analyzed["selected_stream"] = selected_stream
    analyzed["version_banner"] = next(
        (line.strip() for line in selected_raw.splitlines() if line.strip()),
        None,
    )
    return analyzed


def collect_diagnostics(
    chocolatey_query: ChocolateyQuery = _query_chocolatey,
    conda_query: CondaQuery = _query_conda,
    baseline_loader: BaselineLoader = _load_baseline_expectations,
    resolver_loader: ResolverLoader = _load_resolvers,
    command_runner: CommandRunner = _run_command,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Collect every independent observation, retaining failures instead of raising."""

    environment = dict(os.environ if environ is None else environ)
    report: dict[str, object] = {
        "schema_version": 2,
        "environment": {
            "github_actions": environment.get("GITHUB_ACTIONS", "").casefold() == "true",
            "path": environment.get("PATH", ""),
            "chocolatey_install": environment.get("ChocolateyInstall", ""),
            "conda_root": environment.get("CONDA", ""),
            "poppler_prefix": environment.get("RESUME_CI_POPPLER_PREFIX", ""),
            "selected_poppler_directory": environment.get("RESUME_CI_POPPLER_DIR", ""),
            "poppler_install_seconds": environment.get("RESUME_CI_POPPLER_INSTALL_SECONDS", ""),
        },
        "baseline_expectations": {},
        "packages": {"chocolatey": {}, "conda": {}},
        "resolver_import": {"ok": True, "error": ""},
        "resolvers": {},
        "versions": {},
    }

    try:
        report["baseline_expectations"] = baseline_loader()
    except Exception as error:  # diagnostic boundary: retain and continue
        report["baseline_expectations"] = _failure(
            error, category="baseline_expectation_failure"
        )

    chocolatey = report["packages"]["chocolatey"]
    assert isinstance(chocolatey, dict)
    for package in EXPECTED_CHOCOLATEY_PACKAGES:
        try:
            chocolatey[package] = chocolatey_query(package)
        except Exception as error:  # diagnostic boundary: retain and continue
            chocolatey[package] = _failure(error, category="chocolatey_query_failure")

    conda = report["packages"]["conda"]
    assert isinstance(conda, dict)
    conda_root = environment.get("CONDA", "")
    poppler_prefix = environment.get("RESUME_CI_POPPLER_PREFIX", "")
    if not conda_root or not poppler_prefix:
        conda[EXPECTED_CONDA_PACKAGE] = _failure(
            RuntimeError("CONDA and RESUME_CI_POPPLER_PREFIX are required"),
            category="conda_query_failure",
        )
    else:
        try:
            conda[EXPECTED_CONDA_PACKAGE] = conda_query(conda_root, poppler_prefix)
        except Exception as error:  # diagnostic boundary: retain and continue
            conda[EXPECTED_CONDA_PACKAGE] = _failure(
                error, category="conda_query_failure"
            )

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
    timeouts = {
        "libreoffice": LIBREOFFICE_PROBE_TIMEOUT_SECONDS,
        "poppler": POPPLER_PROBE_TIMEOUT_SECONDS,
    }
    for name in ("libreoffice", "poppler"):
        resolver = resolvers.get(name)
        if resolver is None:
            resolver_results[name] = {
                "ok": False,
                "path": "",
                "error": "resolver unavailable after import failure",
            }
            version_results[name] = _analyze_version_result(
                name,
                {
                    "ok": False,
                    "skipped": True,
                    "exit_code": None,
                    "stdout": "",
                    "stderr": "",
                    "error": "version probe skipped because resolver was unavailable",
                },
            )
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
            version_results[name] = _analyze_version_result(
                name,
                {
                    "ok": False,
                    "skipped": True,
                    "exit_code": None,
                    "stdout": "",
                    "stderr": "",
                    "error": "version probe skipped because resolver failed",
                },
            )
            continue
        try:
            result = command_runner((path, commands[name]), timeouts[name])
        except Exception as error:
            result = _failure(error)
        version_results[name] = _analyze_version_result(name, result)

    return report


def _baseline_values(report: Mapping[str, object], failures: list[str]) -> dict[str, str]:
    baseline = report.get("baseline_expectations", {})
    if not isinstance(baseline, Mapping) or not baseline.get("ok"):
        detail = baseline.get("error", "missing result") if isinstance(baseline, Mapping) else "invalid result"
        failures.append(f"Baseline renderer expectations unavailable: {detail}")
        return {}
    values = baseline.get("values", {})
    if not isinstance(values, Mapping):
        failures.append("Baseline renderer expectations are malformed: values are missing")
        return {}
    return {str(key): str(value) for key, value in values.items()}


def evaluate_diagnostics(report: Mapping[str, object]) -> list[str]:
    """Return all verification failures after collection has completed."""

    failures: list[str] = []
    expectations = _baseline_values(report, failures)

    packages = report.get("packages", {})
    if not isinstance(packages, Mapping):
        failures.append("Package diagnostics are missing")
        packages = {}
    chocolatey = packages.get("chocolatey", {})
    if not isinstance(chocolatey, Mapping):
        chocolatey = {}
    for package, expected in EXPECTED_CHOCOLATEY_PACKAGES.items():
        result = chocolatey.get(package, {})
        if not isinstance(result, Mapping) or not result.get("ok"):
            detail = result.get("error", "missing result") if isinstance(result, Mapping) else "invalid result"
            failures.append(f"Chocolatey query failed for {package}: {detail}")
            continue
        lines = {
            line.strip().casefold()
            for line in _probe_value(result).splitlines()
            if line.strip()
        }
        if f"{package}|{expected}".casefold() not in lines:
            failures.append(
                f"Unexpected Chocolatey package version for {package}: {_probe_value(result)!r}"
            )

    conda = packages.get("conda", {})
    if not isinstance(conda, Mapping):
        conda = {}
    poppler_package = conda.get(EXPECTED_CONDA_PACKAGE, {})
    if not isinstance(poppler_package, Mapping) or not poppler_package.get("ok"):
        detail = poppler_package.get("error", "missing result") if isinstance(poppler_package, Mapping) else "invalid result"
        failures.append(f"Conda query failed for {EXPECTED_CONDA_PACKAGE}: {detail}")
    else:
        try:
            records = json.loads(_as_text(poppler_package.get("stdout")))
            if not isinstance(records, list):
                raise ValueError("expected a package-record list")
            exact_records = [
                record
                for record in records
                if isinstance(record, dict)
                and record.get("name") == EXPECTED_CONDA_PACKAGE
            ]
            if len(exact_records) != 1:
                raise ValueError(
                    "expected exactly one record named "
                    f"{EXPECTED_CONDA_PACKAGE!r}; found {len(exact_records)}"
                )
            package_record = exact_records[0]
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            failures.append(f"Conda Poppler metadata is invalid: {error}")
        else:
            expected_poppler = expectations.get("poppler")
            channel_evidence = " ".join(
                str(package_record.get(key, "")) for key in ("channel", "base_url")
            ).casefold()
            if (
                package_record.get("name") != EXPECTED_CONDA_PACKAGE
                or package_record.get("version") != expected_poppler
                or package_record.get("build_string", package_record.get("build"))
                != EXPECTED_CONDA_BUILD
                or "conda-forge" not in channel_evidence
            ):
                failures.append(
                    "Unexpected conda Poppler package identity: "
                    + json.dumps(package_record, sort_keys=True)
                )

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

    libreoffice = versions.get("libreoffice", {})
    if not isinstance(libreoffice, Mapping):
        libreoffice = {}
    if not libreoffice.get("ok"):
        failures.append(
            f"LibreOffice version probe failed: {libreoffice.get('error', 'missing result')}"
        )
    observed_renderer = libreoffice.get("production_renderer_version")
    if observed_renderer is None:
        failures.append(
            "LibreOffice production renderer identity is unavailable: production would record None"
        )
    elif expectations.get("libreoffice") != observed_renderer:
        failures.append(
            f"Unexpected LibreOffice renderer identity: expected={expectations.get('libreoffice')!r} "
            f"observed={observed_renderer!r}"
        )

    poppler = versions.get("poppler", {})
    if not isinstance(poppler, Mapping):
        poppler = {}
    if not poppler.get("ok"):
        failures.append(f"Poppler version probe failed: {poppler.get('error', 'missing result')}")
    expected_banner = (
        f"pdftoppm version {expectations['poppler']}" if expectations.get("poppler") else None
    )
    if poppler.get("version_banner") != expected_banner:
        failures.append(
            f"Unexpected Poppler version banner: expected={expected_banner!r} "
            f"observed={poppler.get('version_banner')!r}"
        )

    environment = report.get("environment", {})
    if isinstance(environment, Mapping) and environment.get("github_actions"):
        for key, label in (
            ("conda_root", "CI CONDA root"),
            ("poppler_prefix", "CI Poppler prefix"),
            ("selected_poppler_directory", "CI Poppler directory"),
            ("poppler_install_seconds", "CI Poppler install duration"),
        ):
            if not str(environment.get(key, "")).strip():
                failures.append(f"{label} was not exported")
        duration = str(environment.get("poppler_install_seconds", ""))
        if duration:
            try:
                if float(duration) < 0:
                    raise ValueError("negative duration")
            except ValueError:
                failures.append(f"CI Poppler install duration is invalid: {duration!r}")
        selected = str(environment.get("selected_poppler_directory", ""))
        resolved = str(poppler.get("path", "")) if isinstance(poppler, Mapping) else ""
        if selected and resolved and os.path.normcase(os.path.abspath(selected)) != os.path.normcase(
            os.path.abspath(str(Path(resolved).parent))
        ):
            failures.append(
                f"CI Poppler directory disagrees with resolver: selected={selected!r} resolved={resolved!r}"
            )

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
    payload = {
        "report": report,
        "failures": list(failures),
        "result": "FAIL" if failures else "PASS",
    }
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
            print(
                f"GitHub step summary unavailable: {type(error).__name__}: {error}",
                file=stream,
            )

    if environment.get("GITHUB_ACTIONS", "").casefold() == "true" and failures:
        compact = json.dumps(
            {"failures": list(failures), "report": report},
            separators=(",", ":"),
            ensure_ascii=False,
        )
        print(
            f"::error title=Renderer pin verification::{_escape_annotation(compact)}",
            file=stream,
        )


def run_probe(
    chocolatey_query: ChocolateyQuery = _query_chocolatey,
    conda_query: CondaQuery = _query_conda,
    baseline_loader: BaselineLoader = _load_baseline_expectations,
    resolver_loader: ResolverLoader = _load_resolvers,
    command_runner: CommandRunner = _run_command,
    environ: Mapping[str, str] | None = None,
    output: TextIO | None = None,
) -> int:
    """Collect, evaluate, and emit one probe with injectable local or CI context."""

    report = collect_diagnostics(
        chocolatey_query,
        conda_query,
        baseline_loader,
        resolver_loader,
        command_runner,
        environ,
    )
    failures = evaluate_diagnostics(report)
    emit_diagnostics(report, failures, environ, output)
    return 1 if failures else 0


def main() -> int:
    return run_probe()


if __name__ == "__main__":
    raise SystemExit(main())
