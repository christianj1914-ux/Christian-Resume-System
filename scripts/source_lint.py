#!/usr/bin/env python3
"""Validate source resume bullets before a JD-specific build selects them."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import build_resume


def main() -> int:
    findings = build_resume.source_resume_lint_findings()
    if not findings:
        print("Source resume lint PASSED: no source bullet issues found.")
        return 0

    print(f"Source resume lint FAILED: {len(findings)} issue(s) found.")
    for finding in findings:
        print(f"- {finding.source}: {finding.rule_id}: {finding.message}")
        print(f"  {finding.excerpt}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
