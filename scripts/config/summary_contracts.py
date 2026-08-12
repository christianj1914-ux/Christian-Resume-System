"""Intentional professional-summary contracts for each document lane."""

COMMERCIAL_SUMMARY_WORD_RANGE = (45, 70)

# Federal summaries stay longer than commercial summaries because they carry
# explicit proof structure for grade, scope, and specialized-experience review.
FEDERAL_SUMMARY_WORD_RANGE = (70, 110)

SUMMARY_SENTENCE_COUNT = 3

SUMMARY_CONTRACTS = {
    "commercial": COMMERCIAL_SUMMARY_WORD_RANGE,
    "federal": FEDERAL_SUMMARY_WORD_RANGE,
}


def summary_word_range(contract: str) -> tuple[int, int]:
    """Resolve a named summary contract or fail with a stable schema error."""
    normalized = (contract or "").strip().lower()
    try:
        return SUMMARY_CONTRACTS[normalized]
    except KeyError as error:
        allowed = ", ".join(sorted(SUMMARY_CONTRACTS))
        raise ValueError(f"Unknown summary contract {contract!r}; expected one of: {allowed}") from error
