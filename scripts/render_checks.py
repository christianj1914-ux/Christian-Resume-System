#!/usr/bin/env python3
"""Render generated Word documents into persistent visual-check folders."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from config.paths import OUTPUT_DIR, PROJECT_ROOT, RENDER_CHECK_DIR
from resolve_python import candidate_paths, resolve_python
from render_manifest import verify_render_directory, write_render_manifest
from workflow_step_runner import ProcessTreeTimeout, run_process_tree_safe


RENDER_ROOT = RENDER_CHECK_DIR


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
    candidates = candidate_paths(PROJECT_ROOT)
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
    resolved = resolve_python(PROJECT_ROOT)
    return str(resolved) if resolved is not None else sys.executable


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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    folder_label = safe_folder_name(label or docx_path.stem)
    output_dir = RENDER_ROOT / f"{timestamp}_{folder_label}_{uuid.uuid4().hex[:8]}"
    output_dir.mkdir(parents=True, exist_ok=False)

    python_executable = render_python_executable()
    command = [
            python_executable,
            str(render_script),
            str(docx_path),
            "--output_dir",
            str(output_dir),
        ]
    try:
        result = run_process_tree_safe(
            command,
            cwd=PROJECT_ROOT,
            timeout_seconds=195,
            phase="DOCX render wrapper",
        )
    except ProcessTreeTimeout as exc:
        print(f"WARNING: {exc}", file=sys.stderr)
        shutil.rmtree(output_dir, ignore_errors=True)
        return None
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
        shutil.rmtree(output_dir, ignore_errors=True)
        return None

    page_count = len(list(output_dir.glob("page-*.png")))
    if page_count == 0:
        print(f"WARNING: render produced no page images for {docx_path.name}", file=sys.stderr)
        shutil.rmtree(output_dir, ignore_errors=True)
        return None
    renderer_executable = str(render_script.resolve())
    renderer_version: str | None = None
    if render_script.name == "render_docx_windows.py":
        try:
            from render_docx_windows import find_soffice

            renderer = find_soffice()
            renderer_executable = str(renderer.resolve())
            version_result = subprocess.run([str(renderer), "--version"], capture_output=True, text=True, timeout=15)
            renderer_version = (version_result.stdout or version_result.stderr).strip() or None
        except (OSError, subprocess.SubprocessError):
            renderer_version = None
    write_render_manifest(
        output_dir,
        docx_path,
        renderer_executable=renderer_executable,
        renderer_version=renderer_version,
        python_executable=python_executable,
    )
    print(f"Render check: {output_dir} ({page_count} page image(s))")
    return output_dir


def final_page_is_sparse(render_dir: Path, *, minimum_vertical_coverage: float = 0.30) -> bool:
    """Return True when the final rendered page has only a stranded tail of text.

    The crop ignores page margins and looks for visibly non-white rows. It is a
    layout guard for document types where a mostly empty final page is not an
    intentional cover sheet.
    """
    verification = verify_render_directory(render_dir)
    if not verification.verified:
        raise ValueError(f"Visual QA is UNVERIFIED: {verification.reason}")
    pages = list(verification.page_files)
    if len(pages) < 2:
        return False
    with Image.open(pages[-1]).convert("RGB") as image:
        width, height = image.size
        left, right = int(width * 0.08), int(width * 0.92)
        top, bottom = int(height * 0.08), int(height * 0.92)
        sample_width = 180
        sample_height = max(1, round((bottom - top) * (sample_width / max(1, right - left))))
        sample = image.crop((left, top, right, bottom)).resize((sample_width, sample_height))
        rows_with_ink: list[int] = []
        for y in range(sample_height):
            row = [sample.getpixel((x, y)) for x in range(sample_width)]
            if sum(1 for red, green, blue in row if min(red, green, blue) < 210) >= 1:
                rows_with_ink.append(y)
        if not rows_with_ink:
            return True
        coverage = (max(rows_with_ink) - min(rows_with_ink) + 1) / sample_height
        return coverage < minimum_vertical_coverage


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
