#!/usr/bin/env python3
"""Generate the shared first-90-days one-pager."""

from __future__ import annotations

import build_interview_companions


def main() -> None:
    build_interview_companions.build_companion(build_interview_companions.FIRST_90_DAYS)


if __name__ == "__main__":
    main()
