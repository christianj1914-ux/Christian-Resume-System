#!/usr/bin/env python3
"""Read-only commercial requirement-parser coverage audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable

from requirement_engine import (
    parse_commercial_posting,
    parse_commercial_requirements_legacy,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = PROJECT_ROOT / "scratch" / "jd_library"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "scratch" / "parser_audit"
DEFAULT_BASELINE = PROJECT_ROOT / "scripts" / "config" / "commercial_parser_audit_baseline.json"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def library_hashes(library: Path) -> dict[str, str]:
    return {
        path.relative_to(library).as_posix(): sha256_path(path)
        for path in sorted(library.rglob("*"))
        if path.is_file()
    }


def _metadata(snapshot_dir: Path) -> dict[str, object]:
    path = snapshot_dir / "metadata.json"
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _header_value(text: str, label: str) -> str:
    prefix = f"{label.lower()}:"
    for raw in text.splitlines()[:12]:
        line = raw.strip()
        if line.lower().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def audit_snapshots(library: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    unique_by_hash: dict[str, dict[str, object]] = {}
    for job_path in sorted(library.glob("*/job_description.txt")):
        metadata = _metadata(job_path.parent)
        if str(metadata.get("workflow_type", "commercial")).lower() == "federal":
            continue
        text = job_path.read_text(encoding="utf-8", errors="replace")
        posting_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        old_requirements = parse_commercial_requirements_legacy(text)
        parsed = parse_commercial_posting(text)
        row: dict[str, object] = {
            "snapshot_id": str(metadata.get("snapshot_id") or job_path.parent.name),
            "company": str(metadata.get("company") or _header_value(text, "Company")),
            "role": str(metadata.get("role") or _header_value(text, "Job Title")),
            "posting_sha256": posting_hash,
            "old_requirement_count": len(old_requirements),
            "new_requirement_count": len(parsed.requirements),
            "parse_mode": parsed.parse_mode,
            "verified": parsed.verified,
            "diagnostics": [
                {"code": diagnostic.code, "message": diagnostic.message}
                for diagnostic in parsed.diagnostics
            ],
        }
        rows.append(row)
        unique_by_hash.setdefault(posting_hash, row)

    unique_rows = list(unique_by_hash.values())
    snapshot_modes = Counter(str(row["parse_mode"]) for row in rows)
    unique_modes = Counter(str(row["parse_mode"]) for row in unique_rows)
    residual = [row for row in unique_rows if row["parse_mode"] == "whole_posting_fallback"]
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "snapshot_total": len(rows),
        "unique_posting_total": len(unique_rows),
        "snapshot_modes": dict(sorted(snapshot_modes.items())),
        "unique_modes": dict(sorted(unique_modes.items())),
        "old_zero_snapshot_count": sum(int(row["old_requirement_count"]) == 0 for row in rows),
        "old_zero_unique_count": sum(int(row["old_requirement_count"]) == 0 for row in unique_rows),
        "whole_posting_fallback_snapshot_count": snapshot_modes["whole_posting_fallback"],
        "whole_posting_fallback_unique_count": unique_modes["whole_posting_fallback"],
        "whole_posting_fallback_unique_percentage": round(
            (100.0 * unique_modes["whole_posting_fallback"] / len(unique_rows)) if unique_rows else 0.0,
            2,
        ),
        "whole_posting_fallbacks": residual,
        "snapshots": rows,
    }


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_ceiling(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("reviewed_unique_whole_posting_fallback_ceiling")
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"Invalid parser-audit ceiling in {path}")
    return value


def _print_summary(result: dict[str, object], report_path: Path, ceiling: int) -> None:
    print("Commercial parser audit")
    print(f"  Snapshots: {result['snapshot_total']}")
    print(f"  Unique postings: {result['unique_posting_total']}")
    print(f"  Legacy zero parses: {result['old_zero_snapshot_count']} snapshots / {result['old_zero_unique_count']} unique")
    print(f"  Snapshot modes: {result['snapshot_modes']}")
    print(f"  Unique modes: {result['unique_modes']}")
    print(
        "  Whole-posting fallback: "
        f"{result['whole_posting_fallback_unique_count']} unique "
        f"({result['whole_posting_fallback_unique_percentage']}%); reviewed ceiling {ceiling}"
    )
    for row in result["whole_posting_fallbacks"]:
        print(f"    - {row['company']} | {row['role']} | {row['snapshot_id']}")
    print(f"  Report: {report_path}")


def run_audit(library: Path, report_dir: Path, baseline: Path) -> int:
    if not library.is_dir():
        raise FileNotFoundError(f"Archive not found: {library}")
    before = library_hashes(library)
    result = audit_snapshots(library)
    after = library_hashes(library)
    if before != after:
        changed = sorted(set(before) | set(after))
        changed = [name for name in changed if before.get(name) != after.get(name)]
        raise RuntimeError(f"Parser audit mutated archive files: {', '.join(changed[:10])}")

    ceiling = _load_ceiling(baseline)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"commercial_parser_audit_{stamp}.json"
    latest_path = report_dir / "latest.json"
    _atomic_json(report_path, result)
    _atomic_json(latest_path, result)
    _print_summary(result, report_path, ceiling)
    fallback_count = int(result["whole_posting_fallback_unique_count"])
    if fallback_count > ceiling:
        print(
            f"ERROR: unique whole-posting fallbacks increased from the reviewed ceiling "
            f"of {ceiling} to {fallback_count}.",
            file=sys.stderr,
        )
        return 1
    return 0


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run_audit(args.library.resolve(), args.report_dir.resolve(), args.baseline.resolve())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
