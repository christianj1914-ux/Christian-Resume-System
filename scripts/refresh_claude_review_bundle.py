#!/usr/bin/env python3
"""Refresh the common Claude Review upload bundle in one pass."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import argparse
from pathlib import Path

import build_claude_prompt
import build_claude_review_packet
import claude_review_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the common Claude Review upload bundle.")
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip validate/integration-test/track-report command capture in generated packets.",
    )
    parser.add_argument(
        "--mode",
        action="append",
        choices=tuple(build_claude_review_packet.PACKET_MODES),
        help="Packet mode to refresh. Defaults to the common broad, resume, interview, federal, and Claude-review bundle.",
    )
    return parser.parse_args()


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def refresh_bundle(modes: tuple[str, ...], *, skip_checks: bool) -> list[Path]:
    written = list(claude_review_bundle.refresh_support_files())
    build_claude_review_packet.clear_command_output_cache()
    for mode in modes:
        packet_path, manifest_path = build_claude_review_packet.write_packet_artifacts(mode, skip_checks=skip_checks)
        written.extend((packet_path, manifest_path))
        for prompt_kind in claude_review_bundle.PROMPT_KINDS:
            prompt_text = build_claude_prompt.build_prompt(prompt_kind, mode, "", str(packet_path))
            prompt_path = write_text(
                build_claude_prompt.default_prompt_output_path(prompt_kind, mode),
                prompt_text,
            )
            written.append(prompt_path)
    return written


def main() -> int:
    args = parse_args()
    modes = tuple(args.mode or claude_review_bundle.DEFAULT_PACKET_MODES)
    written = refresh_bundle(modes, skip_checks=args.skip_checks)
    print(f"Claude Review bundle refreshed: {claude_review_bundle.CLAUDE_REVIEW_DIR}")
    for path in written:
        print(f"- {path.relative_to(claude_review_bundle.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
