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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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
    for name in ("pdftoppm.exe", "pdftoppm", "pdftoppm.cmd"):
        candidates.append(shutil.which(name))
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError("pdftoppm executable not found")


def build_lo_env(profile_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(profile_dir)
    env["XDG_CONFIG_HOME"] = str(profile_dir / "xdg_config")
    env["XDG_CACHE_HOME"] = str(profile_dir / "xdg_cache")
    Path(env["XDG_CONFIG_HOME"]).mkdir(parents=True, exist_ok=True)
    Path(env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
    return env


def run_logged(cmd: list[str], *, env: dict[str, str], verbose: bool) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
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
    result = run_logged(cmd, env=env, verbose=verbose)
    pdf_path = convert_dir / "input.pdf"
    if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0:
        return pdf_path

    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        raise RuntimeError(detail.splitlines()[-1])
    raise RuntimeError(f"LibreOffice conversion failed with exit code {result.returncode}")


def rasterize_pdf(pdf_path: Path, output_dir: Path, *, verbose: bool) -> None:
    pdftoppm = find_pdftoppm()
    prefix = output_dir / "page"
    cmd = [
        pdftoppm,
        "-png",
        str(pdf_path),
        str(prefix),
    ]
    result = run_logged(cmd, env=os.environ.copy(), verbose=verbose)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            raise RuntimeError(detail.splitlines()[-1])
        raise RuntimeError(f"pdftoppm failed with exit code {result.returncode}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a DOCX to page PNGs on Windows.")
    parser.add_argument("input_docx")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--emit_pdf", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_docx = Path(args.input_docx).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codex_render_") as tmp_dir:
        work_dir = Path(tmp_dir)
        pdf_path = convert_docx_to_pdf(input_docx, work_dir, verbose=args.verbose)
        if args.emit_pdf:
            shutil.copy2(pdf_path, output_dir / f"{input_docx.stem}.pdf")
        rasterize_pdf(pdf_path, output_dir, verbose=args.verbose)
    if not list(output_dir.glob("page-*.png")):
        raise SystemExit("No page images were generated")


if __name__ == "__main__":
    main()
