"""Exact-match validator for the Government Warning (ISSUE 2.5).

Unlike the fuzzy/numeric fields handled in `engine.py`, the Government
Warning is legally mandated verbatim text — it must match word-for-word
(after whitespace normalization), and the "GOVERNMENT WARNING" prefix must be
ALL-CAPS. Any deviation is reported as invalid regardless of how close the
text is; there is no fuzzy tolerance (FedRAMP SI-7).
"""

from __future__ import annotations

import re

from app.models import GovernmentWarningCheck

#: The mandated prefix, which must appear in ALL-CAPS.
_REQUIRED_PREFIX = "GOVERNMENT WARNING"

_WHITESPACE_RE = re.compile(r"\s+")


def validate_government_warning(extracted: str | None, expected: str) -> GovernmentWarningCheck:
    """Validate the extracted Government Warning text against the expected text."""
    if extracted is None:
        return GovernmentWarningCheck(
            valid=False,
            issues=["MISSING_TEXT"],
            extracted_text=None,
            expected_text=expected,
        )

    extracted_ws = _collapse_whitespace(extracted)
    expected_ws = _collapse_whitespace(expected)

    issues: list[str] = []

    prefix_issue = _check_prefix(extracted_ws)
    if prefix_issue:
        issues.append(prefix_issue)

    content_issue = _check_content(extracted_ws.lower(), expected_ws.lower())
    if content_issue:
        issues.append(content_issue)

    return GovernmentWarningCheck(
        valid=not issues,
        issues=issues,
        extracted_text=extracted,
        expected_text=expected,
    )


def _collapse_whitespace(value: str) -> str:
    """Collapse runs of spaces/newlines into single spaces and strip the ends."""
    return _WHITESPACE_RE.sub(" ", value).strip()


def _check_prefix(extracted_ws: str) -> str | None:
    """Verify the "GOVERNMENT WARNING" prefix is present and ALL-CAPS."""
    prefix = extracted_ws[: len(_REQUIRED_PREFIX)]
    if prefix.upper() != _REQUIRED_PREFIX:
        return "MISSING_PREFIX"
    if prefix != _REQUIRED_PREFIX:
        return "LOWERCASE_PREFIX"
    return None


def _check_content(extracted_norm: str, expected_norm: str) -> str | None:
    """Compare normalized (whitespace-collapsed, lowercased) text word-for-word."""
    if extracted_norm == expected_norm:
        return None
    if extracted_norm.startswith(expected_norm) and len(extracted_norm) > len(expected_norm):
        return "EXTRA_TEXT"
    if expected_norm.startswith(extracted_norm) and len(extracted_norm) < len(expected_norm):
        return "MISSING_TEXT"
    return "WRONG_TEXT"
