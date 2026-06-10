"""Tests for the Government Warning exact-match validator (ISSUE 2.5)."""

from __future__ import annotations

from matching.exact_validator import validate_government_warning

_GOV_WARNING = (
    "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK "
    "ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. "
    "(2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR "
    "OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS."
)


def test_correct_warning_is_valid():
    result = validate_government_warning(_GOV_WARNING, _GOV_WARNING)

    assert result.valid is True
    assert result.issues == []
    assert result.extracted_text == _GOV_WARNING
    assert result.expected_text == _GOV_WARNING


def test_whitespace_normalization_still_valid():
    extracted = _GOV_WARNING.replace(" ", "\n  ")

    result = validate_government_warning(extracted, _GOV_WARNING)

    assert result.valid is True
    assert result.issues == []


def test_lowercase_prefix_is_invalid():
    extracted = "Government warning: " + _GOV_WARNING.split(": ", 1)[1]

    result = validate_government_warning(extracted, _GOV_WARNING)

    assert result.valid is False
    assert result.issues == ["LOWERCASE_PREFIX"]


def test_missing_prefix_is_invalid():
    extracted = _GOV_WARNING.split(": ", 1)[1]  # body text without the prefix at all

    result = validate_government_warning(extracted, _GOV_WARNING)

    assert result.valid is False
    assert "MISSING_PREFIX" in result.issues


def test_wrong_text_is_invalid():
    extracted = "GOVERNMENT WARNING: THIS PRODUCT CONTAINS SULFITES."

    result = validate_government_warning(extracted, _GOV_WARNING)

    assert result.valid is False
    assert result.issues == ["WRONG_TEXT"]


def test_extra_text_appended_is_invalid():
    extracted = _GOV_WARNING + " ADDITIONAL PROMOTIONAL TEXT."

    result = validate_government_warning(extracted, _GOV_WARNING)

    assert result.valid is False
    assert result.issues == ["EXTRA_TEXT"]


def test_truncated_text_is_missing_text():
    extracted = _GOV_WARNING[: len(_GOV_WARNING) // 2]

    result = validate_government_warning(extracted, _GOV_WARNING)

    assert result.valid is False
    assert result.issues == ["MISSING_TEXT"]


def test_missing_extracted_text_is_invalid():
    result = validate_government_warning(None, _GOV_WARNING)

    assert result.valid is False
    assert result.issues == ["MISSING_TEXT"]
    assert result.extracted_text is None
    assert result.expected_text == _GOV_WARNING
