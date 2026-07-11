#!/usr/bin/env python3
"""Render generated Word documents into persistent visual-check folders."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
RENDER_ROOT = PROJECT_ROOT / "render_check"


def find_render_docx_script() -> Path | None:
    if sys.platform == "win32":
        local_override = PROJECT_ROOT / "scripts" / "render_docx_windows.py"
        if local_override.exists():
            return local_override
    root = Path.home() / ".codex" / "plugins" / "cache" / "openai-primary-runtime" / "documents"
    if not root.is_dir():
        return None
    matches = sorted(root.glob("*/skills/documents/render_docx.py"))
    return matches[-1] if matches else None


RENDER_AVAILABLE = find_render_docx_script() is not None


def _render_python_candidates() -> list[Path]:
    candidates = [
        Path(sys.executable),
        Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe",
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen or not candidate.exists():
            continue
        unique.append(candidate)
        seen.add(key)
    return unique


def render_python_executable() -> str:
    for candidate in _render_python_candidates():
        result = subprocess.run(
            [str(candidate), "-c", "import pdf2image"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return str(candidate)
    return sys.executable


def safe_folder_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip()
    name = re.sub(r"\s+", "_", name)
    return name[:120] or "document"


def ensure_render_root() -> None:
    RENDER_ROOT.mkdir(parents=True, exist_ok=True)
    readme = RENDER_ROOT / "README.txt"
    if not readme.exists():
        readme.write_text(
            "This folder stores timestamped visual render checks for generated Word documents.\n",
            encoding="utf-8",
        )


def render_docx(docx_path: Path, label: str | None = None) -> Path | None:
    docx_path = Path(docx_path)
    if not docx_path.exists():
        print(f"WARNING: render skipped because DOCX does not exist: {docx_path}", file=sys.stderr)
        return None

    render_script = find_render_docx_script()
    if render_script is None:
        print(
            "Render check skipped: render_docx.py not found at expected Codex plugin path. "
            "Visual QA must be done manually. Run the resume in a Codex environment to enable automatic page rendering.",
            file=sys.stderr,
        )
        return None

    ensure_render_root()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_label = safe_folder_name(label or docx_path.stem)
    output_dir = RENDER_ROOT / f"{folder_label}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)

    result = subprocess.run(
        [
            render_python_executable(),
            str(render_script),
            str(docx_path),
            "--output_dir",
            str(output_dir),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        print(f"WARNING: render failed for {docx_path.name}", file=sys.stderr)
        stderr_text = result.stderr.strip()
        if stderr_text:
            if "FileNotFoundError" in stderr_text or "WinError 2" in stderr_text or "CreateProcess" in stderr_text:
                print(
                    "Render check skipped: the local DOCX-to-image converter is unavailable in this environment. "
                    "Visual QA must be done manually.",
                    file=sys.stderr,
                )
            else:
                print(stderr_text, file=sys.stderr)
        return None

    page_count = len(list(output_dir.glob("page-*.png")))
    print(f"Render check: {output_dir} ({page_count} page image(s))")
    return output_dir


def latest_output_docx(count: int) -> list[Path]:
    if not OUTPUT_DIR.is_dir():
        return []
    return sorted(OUTPUT_DIR.glob("*.docx"), key=lambda item: item.stat().st_mtime, reverse=True)[:count]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render generated DOCX files for visual QA.")
    parser.add_argument("docx", nargs="*", type=Path, help="DOCX file(s) to render.")
    parser.add_argument(
        "--latest",
        type=int,
        default=1,
        help="When no DOCX is supplied, render this many latest output DOCX files. Default: 1.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = args.docx or latest_output_docx(args.latest)
    if not paths:
        raise SystemExit("ERROR: no DOCX files found to render.")

    for path in paths:
        render_docx(path)


if __name__ == "__main__":
    main()
