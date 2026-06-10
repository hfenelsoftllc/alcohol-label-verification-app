"""Fuzzy matching engine — compares extracted label fields against application
data (ISSUE 2.4).

Brand, Class/Type, Name & Address, and Country of Origin use RapidFuzz
`token_sort_ratio` (case/punctuation/word-order insensitive). ABV and Net
Contents are compared numerically, after parsing percent/proof and
unit-normalizing volumes, with a tolerance band.

The Government Warning is validated separately and exactly (ISSUE 2.5) — it
is not part of this report. Per FedRAMP SI-10, a field the OCR could not read
(``None``) is reported as `NO_MATCH` rather than raising or being skipped.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from app.models import ApplicationData, ExtractedFields, FieldComparison, MatchReport, MatchStatus, OverallStatus

#: (match threshold, partial-match threshold) for RapidFuzz `token_sort_ratio`.
_FUZZY_THRESHOLDS = {
    "brand": (90.0, 70.0),
    "class_type": (85.0, 65.0),
    "name_address": (80.0, 60.0),
    "country_of_origin": (90.0, 70.0),
}

_PUNCTUATION_RE = re.compile(r"[^\w\s]")

#: ABV tolerance, in percentage points.
_ABV_MATCH_TOLERANCE = 0.5
_ABV_PARTIAL_TOLERANCE = 2.0

#: Net contents tolerance, as a fraction of the expected volume.
_NET_CONTENTS_MATCH_TOLERANCE = 0.01
_NET_CONTENTS_PARTIAL_TOLERANCE = 0.05

_PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
_PROOF_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*proof", re.IGNORECASE)

_NET_CONTENTS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(m\s*l|c\s*l|l|fl\.?\s*oz)\b", re.IGNORECASE)
#: Conversion factor to milliliters for each normalized unit.
_TO_ML = {"ml": 1.0, "cl": 10.0, "l": 1000.0, "floz": 29.5735}


def compare(extracted: ExtractedFields, application_data: ApplicationData) -> MatchReport:
    """Compare extracted label fields against the submitted application data."""
    fields = [
        _compare_fuzzy("brand", extracted.brand, application_data.brand),
        _compare_fuzzy("class_type", extracted.class_type, application_data.class_type),
        _compare_abv(extracted.abv, application_data.abv),
        _compare_net_contents(extracted.net_contents, application_data.net_contents),
        _compare_fuzzy("name_address", extracted.name_address, application_data.name_address),
        _compare_fuzzy("country_of_origin", extracted.country_of_origin, application_data.country_of_origin),
    ]
    return MatchReport(overall_status=_overall_status(fields), fields=fields)


def _overall_status(fields: list[FieldComparison]) -> OverallStatus:
    statuses = {field.status for field in fields}
    if MatchStatus.NO_MATCH in statuses:
        return OverallStatus.FAIL
    if MatchStatus.PARTIAL_MATCH in statuses:
        return OverallStatus.PARTIAL
    return OverallStatus.MATCH


def _compare_fuzzy(field: str, extracted: str | None, expected: str) -> FieldComparison:
    if extracted is None:
        return FieldComparison(field=field, extracted=None, expected=expected, status=MatchStatus.NO_MATCH, score=0.0)

    score = fuzz.token_sort_ratio(_normalize(extracted), _normalize(expected))
    match_threshold, partial_threshold = _FUZZY_THRESHOLDS[field]
    return FieldComparison(
        field=field,
        extracted=extracted,
        expected=expected,
        status=_status_from_score(score, match_threshold, partial_threshold),
        score=score,
    )


def _compare_abv(extracted: str | None, expected: str) -> FieldComparison:
    expected_value = _parse_abv_percent(expected)
    extracted_value = _parse_abv_percent(extracted) if extracted is not None else None

    if extracted_value is None or expected_value is None:
        return FieldComparison(field="abv", extracted=extracted, expected=expected, status=MatchStatus.NO_MATCH, score=0.0)

    diff = abs(extracted_value - expected_value)
    status, score = _tolerance_status(diff, _ABV_MATCH_TOLERANCE, _ABV_PARTIAL_TOLERANCE)
    return FieldComparison(field="abv", extracted=extracted, expected=expected, status=status, score=score)


def _compare_net_contents(extracted: str | None, expected: str) -> FieldComparison:
    expected_ml = _parse_net_contents_ml(expected)
    extracted_ml = _parse_net_contents_ml(extracted) if extracted is not None else None

    if not expected_ml or extracted_ml is None:
        return FieldComparison(
            field="net_contents", extracted=extracted, expected=expected, status=MatchStatus.NO_MATCH, score=0.0
        )

    diff_ratio = abs(extracted_ml - expected_ml) / expected_ml
    status, score = _tolerance_status(diff_ratio, _NET_CONTENTS_MATCH_TOLERANCE, _NET_CONTENTS_PARTIAL_TOLERANCE)
    return FieldComparison(field="net_contents", extracted=extracted, expected=expected, status=status, score=score)


def _normalize(value: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace for fuzzy comparison."""
    return " ".join(_PUNCTUATION_RE.sub("", value).lower().split())


def _status_from_score(score: float, match_threshold: float, partial_threshold: float) -> MatchStatus:
    if score >= match_threshold:
        return MatchStatus.MATCH
    if score >= partial_threshold:
        return MatchStatus.PARTIAL_MATCH
    return MatchStatus.NO_MATCH


def _tolerance_status(diff: float, match_tolerance: float, partial_tolerance: float) -> tuple[MatchStatus, float]:
    """Score a numeric difference against a match/partial tolerance band.

    The score is 100 within `match_tolerance`, falls linearly to 50 at
    `partial_tolerance`, and continues toward 0 beyond that.
    """
    if diff <= match_tolerance:
        return MatchStatus.MATCH, 100.0
    if diff <= partial_tolerance:
        span = partial_tolerance - match_tolerance
        score = 100.0 - 50.0 * (diff - match_tolerance) / span
        return MatchStatus.PARTIAL_MATCH, score
    score = max(0.0, 50.0 - 50.0 * (diff - partial_tolerance) / partial_tolerance)
    return MatchStatus.NO_MATCH, score


def _parse_abv_percent(value: str) -> float | None:
    """Parse an ABV percentage from "XX% Alc. by Vol." or "XX Proof" (Proof / 2)."""
    match = _PERCENT_RE.search(value)
    if match:
        return float(match.group(1))
    match = _PROOF_RE.search(value)
    if match:
        return float(match.group(1)) / 2.0
    return None


def _parse_net_contents_ml(value: str | None) -> float | None:
    """Parse a volume to milliliters, normalizing mL/cL/L/fl oz."""
    if value is None:
        return None
    match = _NET_CONTENTS_RE.search(value)
    if not match:
        return None
    amount, unit = match.groups()
    unit_key = re.sub(r"[\s.]", "", unit).lower()
    return float(amount) * _TO_ML[unit_key]
