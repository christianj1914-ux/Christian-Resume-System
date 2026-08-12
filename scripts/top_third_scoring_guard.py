#!/usr/bin/env python3
"""Guard a future semantic-scoring change; matching is deliberately not enabled yet.

This tripwire must require a corpus diff before any top-third equivalence logic can ship.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROTECTIVE_STATES = {"BRIDGE", "FAIL"}


def load_report(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows", payload)
    if not isinstance(rows, list):
        raise ValueError("Corpus report must contain a list of rows or a top-level 'rows' list.")
    result: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("key"):
            raise ValueError("Each corpus row must include a stable 'key'.")
        result[str(row["key"])] = row
    return result


def unapproved_promotions(
    baseline: dict[str, dict[str, object]],
    candidate: dict[str, dict[str, object]],
    allowed_keys: set[str] | None = None,
) -> tuple[str, ...]:
    allowed = allowed_keys or set()
    promotions: list[str] = []
    for key in sorted(set(baseline) & set(candidate)):
        before = str(baseline[key].get("audit_state", "UNKNOWN")).upper()
        after = str(candidate[key].get("audit_state", "UNKNOWN")).upper()
        if before in PROTECTIVE_STATES and after == "PASS" and key not in allowed:
            promotions.append(key)
    return tuple(promotions)


def compare_reports(
    baseline_path: Path,
    candidate_path: Path,
    *,
    allowlist_path: Path | None = None,
) -> dict[str, object]:
    baseline = load_report(baseline_path)
    candidate = load_report(candidate_path)
    allowlist = set()
    if allowlist_path:
        allowlist = {
            line.strip()
            for line in allowlist_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    promotions = unapproved_promotions(baseline, candidate, allowlist)
    score_changes = {
        key: {
            "before": baseline[key].get("alignment_score"),
            "after": candidate[key].get("alignment_score"),
            "before_state": baseline[key].get("audit_state"),
            "after_state": candidate[key].get("audit_state"),
        }
        for key in sorted(set(baseline) & set(candidate))
        if baseline[key].get("alignment_score") != candidate[key].get("alignment_score")
        or baseline[key].get("audit_state") != candidate[key].get("audit_state")
    }
    return {
        "baseline_rows": len(baseline),
        "candidate_rows": len(candidate),
        "unapproved_bridge_or_fail_to_pass": list(promotions),
        "score_or_state_changes": score_changes,
        "passed": not promotions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--allowlist", type=Path)
    args = parser.parse_args()
    report = compare_reports(args.baseline, args.candidate, allowlist_path=args.allowlist)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit("ERROR: semantic scoring would promote BRIDGE/FAIL output(s) to PASS without an allowlist.")


if __name__ == "__main__":
    main()
