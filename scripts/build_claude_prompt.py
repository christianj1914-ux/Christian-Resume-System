#!/usr/bin/env python3
"""Build a strict Claude prompt that matches a packet mode."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import argparse
import json
import re
import sys
from pathlib import Path

import workspace_health


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_REVIEW_DIR = PROJECT_ROOT / "Claude Review"
PACKET_PATH = CLAUDE_REVIEW_DIR / "TEMP_FOR_REVIEW.md"
TEMPLATE_DIR = PROJECT_ROOT / ".context"
REVIEW_TEMPLATE = TEMPLATE_DIR / "CLAUDE_REVIEW_TEMPLATE.md"
PLAN_TEMPLATE = TEMPLATE_DIR / "CLAUDE_TASK_TEMPLATE.md"
PACKET_MODES = ("broad", "tracker", "checklist", "resume", "cover", "interview", "workflow", "federal", "claude-review")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Claude prompt that matches a packet mode.")
    subparsers = parser.add_subparsers(dest="prompt_kind", required=True)
    for prompt_kind in ("review", "plan"):
        subparser = subparsers.add_parser(prompt_kind)
        subparser.add_argument("--packet-mode", required=True, choices=PACKET_MODES)
        subparser.add_argument("--focus", default="", help="Optional extra focus area for Claude.")
        subparser.add_argument(
            "--packet-path",
            default="",
            help="Optional packet path to reference. Defaults to the mode-specific packet in `Claude Review`.",
        )
        subparser.add_argument(
            "--output",
            type=Path,
            default=None,
            help="Optional path to write the prompt. Defaults to the kind-and-mode-specific file in `Claude Review`.",
        )
        subparser.add_argument(
            "--allow-stale",
            action="store_true",
            help="Allow the default packet path even when its packet manifest is missing or stale.",
        )
    return parser.parse_args()


def default_packet_filename(packet_mode: str) -> str:
    if packet_mode == "broad":
        return "TEMP_FOR_REVIEW.md"
    return f"TEMP_FOR_REVIEW_{packet_mode.upper().replace('-', '_')}.md"


def default_packet_path(packet_mode: str) -> Path:
    return CLAUDE_REVIEW_DIR / default_packet_filename(packet_mode)


def default_prompt_output_path(prompt_kind: str, packet_mode: str) -> Path:
    mode_token = packet_mode.upper().replace("-", "_")
    return CLAUDE_REVIEW_DIR / f"TEMP_CLAUDE_{prompt_kind.upper()}_PROMPT_{mode_token}.txt"


def packet_manifest_path(packet_path: Path) -> Path:
    return packet_path.with_name(f"{packet_path.stem}.manifest.json")


def read_prompt_template(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```text\s*(.*?)```", text, flags=re.S)
    if match:
        return match.group(1).strip()
    return text.strip()


def packet_command(packet_mode: str) -> str:
    return f"python tasks.py claude-packet --mode {packet_mode}"


def review_prompt_command(packet_mode: str) -> str:
    return f"python tasks.py claude-prompt review --packet-mode {packet_mode}"


def plan_prompt_command(packet_mode: str) -> str:
    return f"python tasks.py claude-prompt plan --packet-mode {packet_mode}"


def focus_line(packet_mode: str, focus: str) -> str:
    if focus.strip():
        return f"Focus area: {focus.strip()}"
    return f"Focus area: the primary {packet_mode} logic path and its likely regressions."


def packet_manifest_status(packet_path: Path) -> tuple[bool, str]:
    manifest_path = packet_manifest_path(packet_path)
    if not packet_path.exists():
        return False, f"Missing packet: {packet_path}"
    if not manifest_path.exists():
        return False, f"Missing packet manifest: {manifest_path}"

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded_packet = payload.get("packet_path", "")
    if recorded_packet and Path(recorded_packet).resolve() != packet_path.resolve():
        return False, f"Packet manifest points at a different packet: {recorded_packet}"

    recorded_packet_hash = payload.get("packet_sha256")
    current_packet_hash = workspace_health.sha256_path(packet_path)
    if recorded_packet_hash != current_packet_hash:
        return False, f"Packet file changed since the manifest was written: {packet_path.name}"

    bundle_manifest_raw = payload.get("bundle_manifest_path", "")
    if not bundle_manifest_raw:
        return False, "Packet manifest does not record a bundle manifest path."
    bundle_manifest_path = Path(bundle_manifest_raw)
    if not bundle_manifest_path.exists():
        return False, f"Missing bundle manifest: {bundle_manifest_path}"
    current_bundle_hash = workspace_health.sha256_path(bundle_manifest_path)
    if payload.get("bundle_manifest_sha256") != current_bundle_hash:
        return False, f"Bundle manifest changed after the packet was generated: {bundle_manifest_path.name}"

    for rel_name, expected_hash in payload.get("source_hashes", {}).items():
        if not expected_hash:
            continue
        source_path = PROJECT_ROOT / rel_name
        if not source_path.exists():
            return False, f"Packet source is missing: {rel_name}"
        if workspace_health.sha256_path(source_path) != expected_hash:
            return False, f"Packet source changed after generation: {rel_name}"
    return True, "current"


def build_prompt(prompt_kind: str, packet_mode: str, focus: str, packet_path: str) -> str:
    template_path = REVIEW_TEMPLATE if prompt_kind == "review" else PLAN_TEMPLATE
    template = read_prompt_template(template_path)
    replacements = {
        "{{PACKET_PATH}}": packet_path,
        "{{PACKET_MODE}}": packet_mode,
        "{{PACKET_COMMAND}}": packet_command(packet_mode),
        "{{REVIEW_PROMPT_COMMAND}}": review_prompt_command(packet_mode),
        "{{PLAN_PROMPT_COMMAND}}": plan_prompt_command(packet_mode),
        "{{FOCUS_LINE}}": focus_line(packet_mode, focus),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    residual_placeholders = sorted(set(re.findall(r"{{[^{}]+}}", template)))
    if residual_placeholders:
        joined = ", ".join(residual_placeholders)
        raise ValueError(f"Claude prompt template still contains unreplaced placeholder tokens: {joined}")
    return template.rstrip() + "\n"


def main() -> int:
    args = parse_args()
    explicit_packet_path = args.packet_path.strip()
    packet_path = Path(explicit_packet_path) if explicit_packet_path else default_packet_path(args.packet_mode)
    if not explicit_packet_path:
        current, detail = packet_manifest_status(packet_path)
        if not current:
            if args.allow_stale:
                print(f"WARNING: allowing stale Claude packet: {detail}", file=sys.stderr)
            else:
                raise SystemExit(
                    "Default Claude packet is missing or stale. "
                    f"{detail}. Rebuild it with `python tasks.py claude-packet --mode {args.packet_mode}` "
                    f"or rerun `python tasks.py claude-refresh`, then try again. "
                    "Use `--allow-stale` only when you intentionally want to bypass freshness enforcement."
                )
    elif args.allow_stale:
        print("WARNING: --allow-stale was supplied with an explicit --packet-path; freshness enforcement was already bypassed.", file=sys.stderr)
    prompt = build_prompt(args.prompt_kind, args.packet_mode, args.focus, str(packet_path))
    output_path = args.output or default_prompt_output_path(args.prompt_kind, args.packet_mode)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt, encoding="utf-8")
    print(f"Claude prompt written: {output_path}", file=sys.stderr)
    print(prompt, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
