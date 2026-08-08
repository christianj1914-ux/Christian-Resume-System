#!/usr/bin/env python3
"""Fail fast when source or documentation has unsafe encoding mixtures."""

from __future__ import annotations

import sys
from pathlib import Path


TEXT_SUFFIXES = {".py", ".md"}
UTF8_BOM = b"\xef\xbb\xbf"


def encoding_issues(path: Path) -> list[str]:
    data = path.read_bytes()
    issues: list[str] = []
    if data.startswith(UTF8_BOM):
        issues.append("UTF-8 BOM")
    has_crlf = b"\r\n" in data
    has_lf = b"\n" in data.replace(b"\r\n", b"")
    if has_crlf and has_lf:
        issues.append("mixed CRLF and LF line endings")
    return issues


def main(argv: list[str] | None = None) -> int:
    paths = [Path(value) for value in (argv if argv is not None else sys.argv[1:])]
    failures: list[str] = []
    for path in paths:
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        for issue in encoding_issues(path):
            failures.append(f"{path}: {issue}")
    if failures:
        print("Source encoding hygiene failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
