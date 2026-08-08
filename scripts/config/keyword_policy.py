"""Single keyword-policy interface shared by every commercial workflow."""

from __future__ import annotations

import os


KEYWORD_POLICIES = ("advisory", "balanced", "exhaustive")
DEFAULT_KEYWORD_POLICY = "balanced"


def normalize_keyword_policy(value: str | None) -> str:
    normalized = (value or DEFAULT_KEYWORD_POLICY).strip().lower()
    if normalized not in KEYWORD_POLICIES:
        raise ValueError(
            f"Unsupported keyword policy {value!r}. "
            f"Expected one of: {', '.join(KEYWORD_POLICIES)}"
        )
    return normalized


def active_keyword_policy() -> str:
    return normalize_keyword_policy(
        os.environ.get("RESUME_KEYWORD_POLICY", DEFAULT_KEYWORD_POLICY)
    )
