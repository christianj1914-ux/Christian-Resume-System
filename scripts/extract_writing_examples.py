#!/usr/bin/env python3
"""Extract summary and cover-letter snippets from DOCX examples."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import writing_eval


DEFAULT_OUTPUT_DIR = Path("scratch") / "extracted_writing_examples"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return cleaned or "snippet"


def discover_docx_files(inputs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for entry in inputs:
        if entry.is_file() and entry.suffix.lower() == ".docx":
            files.append(entry)
            continue
        if entry.is_dir():
            files.extend(sorted(path for path in entry.rglob("*.docx") if path.is_file()))
            continue
        raise ValueError(f"Path is not a DOCX file or directory: {entry}")
    unique_files: list[Path] = []
    seen: set[str] = set()
    for path in files:
        resolved = str(path.resolve())
        if resolved not in seen:
            unique_files.append(path)
            seen.add(resolved)
    if not unique_files:
        raise ValueError("No DOCX files found to extract")
    return unique_files


def label_from_path(path: Path) -> str | None:
    lowered_parts = [part.lower() for part in path.parts]
    if "good" in lowered_parts:
        return "good"
    if "bad" in lowered_parts:
        return "bad"
    return None


def build_output_path(output_dir: Path, source_path: Path, section: str) -> Path:
    label = label_from_path(source_path)
    folder = output_dir / label if label else output_dir
    filename = f"{slugify(source_path.stem)}__{section}.txt"
    return folder / filename


def write_sections(source_path: Path, sections: tuple[str, ...], output_dir: Path) -> list[Path]:
    written: list[Path] = []
    for section in sections:
        try:
            text = writing_eval.extract_docx_text(source_path, section)
        except ValueError:
            continue
        output_path = build_output_path(output_dir, source_path, section)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
        written.append(output_path)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract resume summaries and cover-letter sections from DOCX examples into text snippets."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="DOCX files or directories containing DOCX examples.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        choices=writing_eval.DOCX_SECTION_CHOICES,
        help="Section to extract. Repeat the flag for multiple sections. Defaults to all supported sections.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for extracted snippets. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sections = tuple(args.artifact) if args.artifact else writing_eval.DOCX_SECTION_CHOICES
    docx_files = discover_docx_files(args.inputs)
    written_count = 0
    for source_path in docx_files:
        written = write_sections(source_path, sections, args.out_dir)
        if written:
            print(f"{source_path.name}:")
            for path in written:
                print(f"  {path}")
            written_count += len(written)
    if written_count == 0:
        print("No snippets were extracted. Check that the DOCX files contain the requested sections.")
        return 1
    print(f"Extracted {written_count} snippet file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
