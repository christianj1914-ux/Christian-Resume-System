#!/usr/bin/env python3
"""Summarize fresh-corpus keyword-policy safety and disruption."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def integer(row: dict[str, str], key: str) -> int:
    try:
        return int(row.get(key, "0") or 0)
    except ValueError:
        return 0


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def write_combined_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def blocker_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for row in rows:
        blocking_terms = {
            term.strip().lower()
            for term in row.get("balanced_blocker_terms", "").split("|")
            if term.strip()
        }
        try:
            diagnostics = json.loads(row.get("blocker_diagnostics", "[]"))
        except json.JSONDecodeError:
            diagnostics = []
        for item in diagnostics:
            if str(item.get("term", "")).strip().lower() not in blocking_terms:
                continue
            blockers.append(
                {
                    "fixture": row.get("fixture", ""),
                    "target": row.get("target", ""),
                    **item,
                }
            )
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recent-csv", type=Path, required=True)
    parser.add_argument("--legacy-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    recent = read_rows(args.recent_csv)
    legacy = read_rows(args.legacy_csv)
    rows = [*recent, *legacy]
    combined_path = args.output_dir / "fresh_keyword_reliability_combined.csv"
    write_combined_csv(combined_path, rows)

    fingerprints = {row.get("pipeline_fingerprint", "") for row in rows}
    failed_safety: list[str] = []
    if len(rows) != 35:
        failed_safety.append(f"expected 35 complete rows; found {len(rows)}")
    if len(fingerprints) != 1 or not next(iter(fingerprints), ""):
        failed_safety.append("pipeline fingerprint is missing or inconsistent")
    if any(row.get("population") != "fresh_rebuild" for row in rows):
        failed_safety.append("one or more rows are not marked fresh_rebuild")
    if any(row.get("build_exit_state") != "success" for row in rows):
        failed_safety.append("one or more builds did not succeed")
    if any(not truthy(row.get("packaged_audit_passed", "")) for row in rows):
        failed_safety.append("one or more packaged audits did not pass")
    if any(integer(row, "pages") != 2 for row in rows):
        failed_safety.append("one or more resumes are not exactly two pages")
    if any(integer(row, "false_balanced_blockers") for row in rows):
        failed_safety.append("false balanced blockers remain")
    if any(integer(row, "non_requirement_balanced_blockers") for row in rows):
        failed_safety.append("non-requirement balanced blockers remain")
    if any(not truthy(row.get("direct_workflow_gating_parity", "")) for row in rows):
        failed_safety.append("direct and workflow policy gating diverge")
    if any(integer(row, "balanced_blockers") > integer(row, "supported_core_unwritten") for row in rows):
        failed_safety.append("balanced blocks a term outside the supported-core set")

    disrupted = [row for row in rows if integer(row, "balanced_blockers") > 0]
    blocker_count = sum(integer(row, "balanced_blockers") for row in rows)
    disruption_rate = (100.0 * len(disrupted) / len(rows)) if rows else 0.0
    safety_passed = not failed_safety
    recommendation = (
        "Option A: the clean gate passed. Apply the conditionally pre-approved one-line promotion "
        "to balanced, retain advisory/exhaustive overrides, and run post-switch parity checks."
        if safety_passed and not disrupted
        else (
            "Option B: retain advisory and consider a separately approved targeted placement pass "
            "for the genuine survivors before promotion."
            if safety_passed
            else "Option B: keep advisory. The fresh measurement did not clear every safety gate."
        )
    )
    survivors = blocker_rows(rows)

    summary_path = args.output_dir / "fresh_keyword_reliability_summary.md"
    summary_path.write_text(
        "\n".join(
            [
                "# Fresh Keyword Reliability Measurement",
                "",
                f"- Fresh builds: {len(rows)}/35",
                f"- Pipeline fingerprint: `{next(iter(fingerprints), '')}`",
                f"- Safety: {'PASS' if safety_passed else 'INCONCLUSIVE/FAIL'}",
                f"- Legitimately disrupted builds: {len(disrupted)}/{len(rows)} ({disruption_rate:.1f}%)",
                f"- Supported core blocker instances: {blocker_count}",
                f"- False/non-requirement blockers: "
                f"{sum(integer(row, 'false_balanced_blockers') + integer(row, 'non_requirement_balanced_blockers') for row in rows)}",
                "",
                "## Safety findings",
                "",
                *(f"- {finding}" for finding in failed_safety),
                *(["- None"] if not failed_safety else []),
                "",
                "## Decision",
                "",
                recommendation,
                "",
                "The earlier archived-output figure of 47 supported core misses is retained only as a "
                "historical upper bound and is not used for this decision.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    packet_path = args.output_dir / "CLAUDE_REVIEW_fresh_balanced_promotion.md"
    survivor_lines = [
        f"- `{item['fixture']}` -- **{item['term']}** ({item['disposition']}), "
        f"concept `{item.get('catalog_concept') or 'none'}`; "
        f"requirements: {', '.join(item.get('validating_requirements') or []) or 'not resolved'}"
        for item in survivors
    ]
    packet_path.write_text(
        "\n".join(
            [
                "# Claude Review: Fresh-Corpus Balanced Promotion",
                "",
                "## Evidence",
                "",
                f"- Safety: {'PASS' if safety_passed else 'INCONCLUSIVE/FAIL'}",
                f"- Fresh builds measured: {len(rows)}/35",
                f"- Genuine-blocker disruption: {len(disrupted)}/{len(rows)} builds ({disruption_rate:.1f}%)",
                f"- Genuine supported core blocker instances: {blocker_count}",
                f"- Safety failures: {len(failed_safety)}",
                "",
                "## Option A -- Promote balanced under the conditional pre-approval",
                "",
                "Use only if safety passes with zero supported-core disruption. The user conditionally "
                "pre-approved this clean path. Change the centralized default to balanced; retain explicit "
                "advisory and exhaustive overrides; update help and documentation; then rerun direct/workflow "
                "and dependent-document parity. Rollback is the one-line constant change back to advisory.",
                "",
                "## Option B -- Keep advisory",
                "",
                "Required if any safety gate fails. Also available when safety passes but the user considers the "
                "genuine-blocker disruption rate too high. Surviving blockers should move to a separately approved "
                "targeted placement pass.",
                "",
                "## Genuine survivors",
                "",
                *(survivor_lines or ["- None"]),
                "",
                "## Recommendation",
                "",
                recommendation,
                "",
                (
                    "The clean result authorizes the pre-approved production-default promotion."
                    if safety_passed and not disrupted
                    else "Production must remain advisory because the clean promotion gate did not pass."
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(summary_path)
    print(packet_path)
    return 0 if safety_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
