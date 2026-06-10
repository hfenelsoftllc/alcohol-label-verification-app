"""Tests for the OCR text-to-fields parser (ISSUE 2.3)."""

from __future__ import annotations

import pytest

from app.models import LABEL_FIELD_NAMES
from ocr import parser

_GOV_WARNING_TEXT = (
    "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT "
    "DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH "
    "DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO "
    "DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS."
)


def test_domestic_whiskey_label():
    text = (
        "OLD HARBOR\n"
        "Kentucky Straight Bourbon Whiskey\n"
        "45% Alc. by Vol. (90 Proof)\n"
        "750 mL\n"
        "Distilled and Bottled by Old Harbor Distilling Co.\n"
        "1500 Distillery Road, Bardstown, KY 40004\n"
        f"{_GOV_WARNING_TEXT}\n"
    )

    fields = parser.parse_raw_text(text)

    assert set(fields.keys()) == set(LABEL_FIELD_NAMES)
    assert fields["brand"] == "OLD HARBOR"
    assert fields["class_type"] == "Kentucky Straight Bourbon Whiskey"
    assert fields["abv"] == "45% Alc. by Vol."
    assert fields["net_contents"] == "750 mL"
    assert fields["name_address"] == (
        "Distilled and Bottled by Old Harbor Distilling Co., "
        "1500 Distillery Road, Bardstown, KY 40004"
    )
    assert fields["country_of_origin"] is None
    assert fields["government_warning"] == _GOV_WARNING_TEXT


def test_imported_wine_label_with_country_of_origin():
    text = (
        "CHATEAU MARGAUX VALLEY\n"
        "Cabernet Sauvignon\n"
        "13.5% Alc. by Vol.\n"
        "750 mL\n"
        "Imported by Global Wine Imports\n"
        "500 Park Ave, New York, NY 10022\n"
        "Product of France\n"
        f"{_GOV_WARNING_TEXT}\n"
    )

    fields = parser.parse_raw_text(text)

    assert fields["brand"] == "CHATEAU MARGAUX VALLEY"
    assert fields["class_type"] == "Cabernet Sauvignon"
    assert fields["abv"] == "13.5% Alc. by Vol."
    assert fields["net_contents"] == "750 mL"
    assert fields["country_of_origin"] == "France"
    # The address block stops once the "Product of France" line is reached.
    assert fields["name_address"] == (
        "Imported by Global Wine Imports, 500 Park Ave, New York, NY 10022"
    )
    assert fields["government_warning"] == _GOV_WARNING_TEXT


def test_made_in_pattern_and_cl_normalization():
    text = (
        "AMARO della NOTTE\n"
        "Liqueur\n"
        "28% Alc. by Vol.\n"
        "70CL\n"
        "Imported by Global Wine Imports\n"
        "500 Park Ave, New York, NY 10022\n"
        "Made in Italy\n"
        f"{_GOV_WARNING_TEXT}\n"
    )

    fields = parser.parse_raw_text(text)

    assert fields["class_type"] == "Liqueur"
    assert fields["net_contents"] == "70 cL"
    assert fields["country_of_origin"] == "Italy"


def test_ocr_noise_merged_characters_and_split_government_warning():
    """Merged ABV/net-contents characters and a "GOVERNMENT\\nWARNING" line break."""
    text = (
        "SUNSET RIDGE\n"
        "Pinot Noir\n"
        "13.5%Alc.byVol.\n"
        "750ML\n"
        "GOVERNMENT\n"
        f"{_GOV_WARNING_TEXT.removeprefix('GOVERNMENT ')}\n"
    )

    fields = parser.parse_raw_text(text)

    assert fields["brand"] == "SUNSET RIDGE"
    assert fields["class_type"] == "Pinot Noir"
    # ABV is reported exactly as printed/OCR'd — only net contents is normalized.
    assert fields["abv"] == "13.5%Alc.byVol."
    assert fields["net_contents"] == "750 mL"
    assert fields["government_warning"] == _GOV_WARNING_TEXT


def test_brand_normalizes_internal_whitespace():
    fields = parser.parse_raw_text("STONE'S    THROW\nVodka\n40% Alc. by Vol.\n")
    assert fields["brand"] == "STONE'S THROW"


def test_proof_pattern_without_percent():
    fields = parser.parse_raw_text("RESERVE\nBourbon\n90 Proof\n750 mL\n")
    assert fields["abv"] == "90 Proof"
    assert fields["class_type"] == "Bourbon"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("750ml", "750 mL"),
        ("750 ML", "750 mL"),
        ("1.75L", "1.75 L"),
        ("1.75 l", "1.75 L"),
        ("70CL", "70 cL"),
        ("12FLOZ", "12 fl oz"),
        ("12 fl. oz.", "12 fl oz"),
    ],
)
def test_net_contents_unit_normalization(raw, expected):
    fields = parser.parse_raw_text(f"BRAND NAME\nVodka\n{raw}\n")
    assert fields["net_contents"] == expected


@pytest.mark.parametrize(
    "class_type_line",
    [
        "Premium Vodka",
        "Kentucky Straight Bourbon Whiskey",
        "India Pale Ale",
        "Cabernet Sauvignon",
        "Sparkling Wine",
    ],
)
def test_class_type_keyword_proximity(class_type_line):
    text = f"BRAND NAME\n{class_type_line}\n40% Alc. by Vol.\n750 mL\n"
    fields = parser.parse_raw_text(text)
    assert fields["class_type"] == class_type_line


def test_empty_text_returns_all_none_fields():
    fields = parser.parse_raw_text("   \n\n  \t\n")
    assert set(fields.keys()) == set(LABEL_FIELD_NAMES)
    assert all(value is None for value in fields.values())


def test_no_government_warning_present():
    fields = parser.parse_raw_text("BRAND NAME\nVodka\n40% Alc. by Vol.\n750 mL\n")
    assert fields["government_warning"] is None
