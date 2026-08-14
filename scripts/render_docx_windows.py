#!/usr/bin/env python3
"""Windows-focused DOCX render helper for local build validation.

This mirrors the external render_docx.py contract closely enough for the
resume builders: it renders a DOCX into page-<N>.png images inside the
requested output directory and optionally leaves behind the generated PDF.

Why this exists:
- The bundled render_docx.py relies on a bare "soffice" lookup plus a
  Windows-incompatible UserInstallation URI.
- On this machine, LibreOffice is installed but not exposed that way.

This helper keeps the workflow inside the repo and uses the real
`soffice.com` console wrapper directly.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from workflow_step_runner import ProcessTreeTimeout, run_process_tree_safe
from render_manifest import write_render_manifest


LIBREOFFICE_TIMEOUT_SECONDS = 120
PDFINFO_TIMEOUT_SECONDS = 15
RASTERIZATION_BASE_SECONDS = 30
RASTERIZATION_SECONDS_PER_PAGE = 1.5
RASTERIZATION_MAX_SECONDS = 300
RASTERIZATION_UNKNOWN_PAGE_SECONDS = 90


class RenderPhaseTimeout(TimeoutError):
    """A renderer timeout with enough workload context to diagnose the bound."""

    def __init__(self, phase: str, page_count: int | None, computed_bound: float, elapsed: float) -> None:
        page_label = str(page_count) if page_count is not None else "unknown"
        super().__init__(
            f"{phase} timed out: page_count={page_label}; "
            f"computed_bound={computed_bound:.1f}s; elapsed={elapsed:.1f}s"
        )
        self.phase = phase
        self.page_count = page_count
        self.computed_bound = computed_bound
        self.elapsed = elapsed


def find_soffice() -> Path:
    candidates: list[str | None] = [
        shutil.which("soffice.com"),
        shutil.which("soffice.exe"),
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.com",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.com",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return path
    raise FileNotFoundError("LibreOffice soffice executable not found")


def find_pdftoppm() -> str:
    candidates: list[str | None] = []
    python_dir = Path(sys.executable).resolve().parent
    dependencies_root = python_dir.parent if python_dir.name == "python" else None
    if dependencies_root is not None:
        candidates.append(
            str(
                dependencies_root
                / "native"
                / "poppler"
                / "Library"
                / "bin"
                / "pdftoppm.exe"
            )
        )
    # Prefer the real bundled executable over the command-wrapper shims that
    # can resolve to a missing DLL or an invalid working directory on Windows.
    runtime_native = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "native" / "poppler" / "Library" / "bin" / "pdftoppm.exe"
    candidates.append(str(runtime_native))
    for name in ("pdftoppm.exe", "pdftoppm", "pdftoppm.cmd"):
        candidates.append(shutil.which(name))
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError("pdftoppm executable not found")


def find_pdfinfo(pdftoppm: str | None = None) -> str:
    """Find pdfinfo in the selected Poppler installation before consulting PATH."""
    rasterizer = Path(pdftoppm or find_pdftoppm())
    candidates: list[str | None] = [
        str(rasterizer.with_name("pdfinfo.exe")),
        str(rasterizer.with_name("pdfinfo")),
        str(rasterizer.with_name("pdfinfo.cmd")),
        shutil.which("pdfinfo.exe"),
        shutil.which("pdfinfo"),
        shutil.which("pdfinfo.cmd"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError("pdfinfo executable not found")


def build_lo_env(profile_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["RESUME_LO_PROFILE_ROOT"] = str(profile_dir)
    return env


def run_logged(
    cmd: list[str],
    *,
    env: dict[str, str],
    verbose: bool,
    timeout_seconds: float,
    phase: str,
) -> subprocess.CompletedProcess[str]:
    result = run_process_tree_safe(
        cmd,
        env=env,
        timeout_seconds=timeout_seconds,
        phase=phase,
    )
    if verbose:
        print("[render_docx_windows] $ " + " ".join(cmd))
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
    return result


def convert_docx_to_pdf(input_docx: Path, work_dir: Path, *, verbose: bool) -> Path:
    soffice = find_soffice()
    convert_dir = work_dir / "convert"
    convert_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = work_dir / "soffice_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    env = build_lo_env(profile_dir)
    profile_uri = profile_dir.resolve().as_uri()

    # LibreOffice on Windows is more reliable here when the input DOCX lives in
    # a temp folder with a short, space-free name.
    staged_docx = work_dir / "input.docx"
    shutil.copy2(input_docx, staged_docx)

    cmd = [
        str(soffice),
        f"-env:UserInstallation={profile_uri}",
        "--invisible",
        "--headless",
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(convert_dir),
        str(staged_docx),
    ]
    # PDF page count does not exist until conversion completes, so conversion
    # retains its own fixed bound while rasterization scales with actual pages.
    started = time.monotonic()
    try:
        result = run_logged(
            cmd,
            env=env,
            verbose=verbose,
            timeout_seconds=LIBREOFFICE_TIMEOUT_SECONDS,
            phase="LibreOffice conversion",
        )
    except ProcessTreeTimeout as exc:
        raise RenderPhaseTimeout(
            "LibreOffice conversion",
            None,
            float(LIBREOFFICE_TIMEOUT_SECONDS),
            time.monotonic() - started,
        ) from exc
    pdf_path = convert_dir / "input.pdf"
    if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0:
        return pdf_path

    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        raise RuntimeError(detail.splitlines()[-1])
    raise RuntimeError(f"LibreOffice conversion failed with exit code {result.returncode}")


def parse_pdf_page_count(output: str) -> int:
    match = re.search(r"^Pages:\s*(\d+)\s*$", output, flags=re.IGNORECASE | re.MULTILINE)
    if not match or int(match.group(1)) < 1:
        raise ValueError("pdfinfo output did not contain a positive Pages value")
    return int(match.group(1))


def expected_pdf_page_count(pdf_path: Path, pdftoppm: str, *, verbose: bool) -> int | None:
    try:
        pdfinfo = find_pdfinfo(pdftoppm)
        result = run_logged(
            [pdfinfo, str(pdf_path)],
            env=os.environ.copy(),
            verbose=verbose,
            timeout_seconds=PDFINFO_TIMEOUT_SECONDS,
            phase="PDF page-count probe",
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(detail.splitlines()[-1] if detail else f"pdfinfo exited {result.returncode}")
        return parse_pdf_page_count(result.stdout)
    except (FileNotFoundError, ProcessTreeTimeout, RuntimeError, ValueError) as exc:
        print(
            "WARNING: PDF page count unavailable; "
            f"using {RASTERIZATION_UNKNOWN_PAGE_SECONDS}s rasterization fallback: {exc}",
            file=sys.stderr,
        )
        return None


def rasterization_timeout_seconds(expected_pages: int | None) -> float:
    if expected_pages is None:
        return float(RASTERIZATION_UNKNOWN_PAGE_SECONDS)
    if expected_pages < 1:
        raise ValueError("expected page count must be positive")
    return min(
        float(RASTERIZATION_MAX_SECONDS),
        RASTERIZATION_BASE_SECONDS + RASTERIZATION_SECONDS_PER_PAGE * expected_pages,
    )


def rasterize_pdf(pdf_path: Path, output_dir: Path, *, verbose: bool) -> None:
    pdftoppm = find_pdftoppm()
    page_count = expected_pdf_page_count(pdf_path, pdftoppm, verbose=verbose)
    timeout_seconds = rasterization_timeout_seconds(page_count)
    prefix = output_dir / "page"
    cmd = [
        pdftoppm,
        "-png",
        str(pdf_path),
        str(prefix),
    ]
    started = time.monotonic()
    try:
        result = run_logged(
            cmd,
            env=os.environ.copy(),
            verbose=verbose,
            timeout_seconds=timeout_seconds,
            phase="PDF rasterization",
        )
    except ProcessTreeTimeout as exc:
        raise RenderPhaseTimeout(
            "PDF rasterization",
            page_count,
            timeout_seconds,
            time.monotonic() - started,
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            raise RuntimeError(detail.splitlines()[-1])
        raise RuntimeError(f"pdftoppm failed with exit code {result.returncode}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a DOCX to page PNGs on Windows.")
    parser.add_argument("input_docx")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_docx = Path(args.input_docx).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="codex_render_") as tmp_dir:
            work_dir = Path(tmp_dir)
            pdf_path = convert_docx_to_pdf(input_docx, work_dir, verbose=args.verbose)
            rasterize_pdf(pdf_path, output_dir, verbose=args.verbose)
    except (ProcessTreeTimeout, RenderPhaseTimeout) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    if not list(output_dir.glob("page-*.png")):
        raise SystemExit("No page images were generated")
    renderer = find_soffice()
    renderer_version: str | None = None
    try:
        version_result = subprocess.run([str(renderer), "--version"], capture_output=True, text=True, timeout=15)
        renderer_version = (version_result.stdout or version_result.stderr).strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    write_render_manifest(
        output_dir,
        input_docx,
        renderer_executable=str(renderer.resolve()),
        renderer_version=renderer_version,
        python_executable=sys.executable,
    )


if __name__ == "__main__":
    main()
