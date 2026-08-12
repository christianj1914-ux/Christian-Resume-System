"""Bind rendered page images to the exact DOCX that produced them."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class RenderVerification:
    verified: bool
    status: str
    reason: str
    page_files: tuple[Path, ...] = ()
    manifest: dict[str, Any] | None = None

    @property
    def page_count(self) -> int:
        return len(self.page_files)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ordered_page_files(render_dir: Path) -> tuple[Path, ...]:
    def page_key(item: Path) -> tuple[int, str]:
        match = re.search(r"(\d+)$", item.stem)
        return (int(match.group(1)) if match else sys.maxsize, item.name)

    return tuple(sorted(Path(render_dir).glob("page-*.png"), key=page_key))


def _write_payload(manifest_path: Path, payload: dict[str, Any]) -> Path:
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, manifest_path)
    return manifest_path


def write_render_manifest(
    render_dir: Path,
    source_docx: Path,
    *,
    renderer_executable: str,
    renderer_version: str | None,
    python_executable: str,
) -> Path:
    render_dir = Path(render_dir).resolve()
    source_docx = Path(source_docx).resolve()
    pages = ordered_page_files(render_dir)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_path": str(source_docx),
        "source_docx_sha256": file_sha256(source_docx),
        "renderer_executable": renderer_executable,
        "renderer_version": renderer_version,
        "python_executable": python_executable,
        "rendered_at_utc": datetime.now(timezone.utc).isoformat(),
        "page_count": len(pages),
        "page_filenames": [page.name for page in pages],
    }
    manifest_path = render_dir / MANIFEST_NAME
    return _write_payload(manifest_path, payload)


def rebind_render_manifest(render_dir: Path, published_source: Path, *, content_source: Path | None = None) -> Path:
    """Point a validated staging render at its byte-identical published path."""
    manifest_path = Path(render_dir).resolve() / MANIFEST_NAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    comparison_source = Path(content_source or published_source).resolve()
    if not comparison_source.is_file():
        raise FileNotFoundError(f"render manifest rebind source is missing: {comparison_source}")
    if file_sha256(comparison_source) != payload.get("source_docx_sha256"):
        raise ValueError("published render source does not match the staged DOCX hash")
    payload["source_path"] = str(Path(published_source).resolve())
    return _write_payload(manifest_path, payload)


def verify_render_directory(render_dir: Path, source_docx: Path | None = None) -> RenderVerification:
    render_dir = Path(render_dir).resolve()
    manifest_path = render_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        return RenderVerification(False, "UNVERIFIED", f"render manifest is missing: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return RenderVerification(False, "UNVERIFIED", f"render manifest is unreadable: {error}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        return RenderVerification(False, "UNVERIFIED", f"unsupported render manifest schema: {payload.get('schema_version')}", manifest=payload)

    recorded_source = Path(str(payload.get("source_path", "")))
    expected_source = Path(source_docx).resolve() if source_docx is not None else recorded_source.resolve()
    if source_docx is not None and recorded_source.resolve() != expected_source:
        return RenderVerification(False, "UNVERIFIED", "render manifest points to a different source DOCX", manifest=payload)
    if not expected_source.is_file():
        return RenderVerification(False, "UNVERIFIED", f"source DOCX is missing: {expected_source}", manifest=payload)
    if file_sha256(expected_source) != payload.get("source_docx_sha256"):
        return RenderVerification(False, "UNVERIFIED", "source DOCX hash no longer matches the render manifest", manifest=payload)

    recorded_names = payload.get("page_filenames")
    if not isinstance(recorded_names, list) or not all(isinstance(name, str) for name in recorded_names):
        return RenderVerification(False, "UNVERIFIED", "render manifest page list is invalid", manifest=payload)
    pages = ordered_page_files(render_dir)
    actual_names = [page.name for page in pages]
    if actual_names != recorded_names or len(pages) != payload.get("page_count"):
        return RenderVerification(False, "UNVERIFIED", "render page files or count do not match the manifest", manifest=payload)
    if not pages:
        return RenderVerification(False, "UNVERIFIED", "render manifest contains no page images", manifest=payload)
    return RenderVerification(True, "VERIFIED", "source hash and page inventory match", pages, payload)
