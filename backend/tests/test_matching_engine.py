"""Tests for the fuzzy matching engine (ISSUE 2.4)."""

from __future__ import annotations

from app.models import ApplicationData, ExtractedFields, FieldComparison, MatchReport, MatchStatus, OverallStatus
from matching import engine

_FIELD_NAMES = ("brand", "class_type", "abv", "net_contents", "name_address", "country_of_origin")


def _application_data(**overrides) -> ApplicationData:
    defaults = dict(
        brand="Stone's Throw",
        class_type="Vodka",
        abv="40% Alc. by Vol.",
        net_contents="750 mL",
        name_address="Old Harbor Distilling Co., 1500 Distillery Road, Bardstown, KY 40004",
        country_of_origin="United States",
        government_warning="GOVERNMENT WARNING: ...",
    )
    defaults.update(overrides)
    return ApplicationData(**defaults)


def _extracted_fields(**overrides) -> ExtractedFields:
    defaults = dict(
        brand="Stone's Throw",
        class_type="Vodka",
        abv="40% Alc. by Vol.",
        net_contents="750 mL",
        name_address="Old Harbor Distilling Co., 1500 Distillery Road, Bardstown, KY 40004",
        country_of_origin="United States",
        government_warning="GOVERNMENT WARNING: ...",
    )
    defaults.update(overrides)
    return ExtractedFields(**defaults)


def _field(report: MatchReport, name: str) -> FieldComparison:
    return next(f for f in report.fields if f.field == name)


def test_field_order_matches_label_fields():
    report = engine.compare(_extracted_fields(), _application_data())
    assert [f.field for f in report.fields] == list(_FIELD_NAMES)


def test_exact_match_all_fields():
    report = engine.compare(_extracted_fields(), _application_data())

    assert report.overall_status == OverallStatus.MATCH
    assert {f.status for f in report.fields} == {MatchStatus.MATCH}
    assert all(f.score == 100.0 for f in report.fields)


def test_minor_variation_partial_match():
    extracted = _extracted_fields(
        abv="41% Alc. by Vol.",  # 1.0 point off -> within partial tolerance
        country_of_origin="United States of America",  # token_sort_ratio ~70
    )

    report = engine.compare(extracted, _application_data())

    assert report.overall_status == OverallStatus.PARTIAL
    statuses = {f.field: f.status for f in report.fields}
    assert statuses["abv"] == MatchStatus.PARTIAL_MATCH
    assert statuses["country_of_origin"] == MatchStatus.PARTIAL_MATCH
    assert MatchStatus.NO_MATCH not in statuses.values()


def test_completely_wrong_fail():
    extracted = _extracted_fields(
        brand="Acme Beverage Corp",
        class_type="Whiskey",
        abv="5% Alc. by Vol.",
        net_contents="50 mL",
        name_address="456 Industrial Blvd, Nowhere, TX 75001",
        country_of_origin="France",
    )

    report = engine.compare(extracted, _application_data(class_type="Premium Vodka"))

    assert report.overall_status == OverallStatus.FAIL
    assert all(f.status == MatchStatus.NO_MATCH for f in report.fields)


# --- Brand (fuzzy, >= 90% match / >= 70% partial) -----------------------------


def test_brand_match():
    report = engine.compare(_extracted_fields(brand="Stone's Throw"), _application_data())
    field = _field(report, "brand")
    assert field.status == MatchStatus.MATCH
    assert field.score == 100.0


def test_brand_partial_match():
    report = engine.compare(_extracted_fields(brand="Stone's Throw Vodka"), _application_data())
    field = _field(report, "brand")
    assert field.status == MatchStatus.PARTIAL_MATCH


def test_brand_no_match():
    report = engine.compare(_extracted_fields(brand="Acme Beverage Corp"), _application_data())
    field = _field(report, "brand")
    assert field.status == MatchStatus.NO_MATCH
    assert field.extracted == "Acme Beverage Corp"
    assert field.expected == "Stone's Throw"


# --- Class/Type (fuzzy, >= 85% match / >= 65% partial) ------------------------


def test_class_type_match():
    report = engine.compare(_extracted_fields(class_type="Vodka"), _application_data(class_type="Vodka"))
    assert _field(report, "class_type").status == MatchStatus.MATCH


def test_class_type_partial_match():
    report = engine.compare(
        _extracted_fields(class_type="Cabernet Sauvignon Reserve"),
        _application_data(class_type="Cabernet Sauvignon"),
    )
    assert _field(report, "class_type").status == MatchStatus.PARTIAL_MATCH


def test_class_type_no_match():
    report = engine.compare(
        _extracted_fields(class_type="Whiskey"),
        _application_data(class_type="Premium Vodka"),
    )
    assert _field(report, "class_type").status == MatchStatus.NO_MATCH


# --- ABV (numeric, +/-0.5pp match / +/-2pp partial) ---------------------------


def test_abv_within_tolerance_matches():
    report = engine.compare(_extracted_fields(abv="40.4% Alc. by Vol."), _application_data(abv="40% Alc. by Vol."))
    field = _field(report, "abv")
    assert field.status == MatchStatus.MATCH
    assert field.score == 100.0


def test_abv_partial_match():
    report = engine.compare(_extracted_fields(abv="41% Alc. by Vol."), _application_data(abv="40% Alc. by Vol."))
    field = _field(report, "abv")
    assert field.status == MatchStatus.PARTIAL_MATCH
    assert 0.0 < field.score < 100.0


def test_abv_no_match():
    report = engine.compare(_extracted_fields(abv="5% Alc. by Vol."), _application_data(abv="40% Alc. by Vol."))
    field = _field(report, "abv")
    assert field.status == MatchStatus.NO_MATCH
    assert field.score == 0.0


def test_abv_proof_converted_to_percent():
    report = engine.compare(_extracted_fields(abv="80 Proof"), _application_data(abv="40% Alc. by Vol."))
    assert _field(report, "abv").status == MatchStatus.MATCH


def test_abv_missing_extracted_is_no_match():
    report = engine.compare(_extracted_fields(abv=None), _application_data(abv="40% Alc. by Vol."))
    field = _field(report, "abv")
    assert field.status == MatchStatus.NO_MATCH
    assert field.score == 0.0
    assert field.extracted is None


# --- Net Contents (numeric, +/-1% match / +/-5% partial, unit-normalized) -----


def test_net_contents_unit_normalization_matches():
    report = engine.compare(_extracted_fields(net_contents="0.75 L"), _application_data(net_contents="750 mL"))
    field = _field(report, "net_contents")
    assert field.status == MatchStatus.MATCH
    assert field.score == 100.0


def test_net_contents_partial_match():
    report = engine.compare(_extracted_fields(net_contents="740 mL"), _application_data(net_contents="750 mL"))
    assert _field(report, "net_contents").status == MatchStatus.PARTIAL_MATCH


def test_net_contents_no_match():
    report = engine.compare(_extracted_fields(net_contents="375 mL"), _application_data(net_contents="750 mL"))
    field = _field(report, "net_contents")
    assert field.status == MatchStatus.NO_MATCH
    assert field.score == 0.0


# --- Name & Address (fuzzy, >= 80% match / >= 60% partial) --------------------


def test_name_address_minor_formatting_difference_matches():
    report = engine.compare(
        _extracted_fields(name_address="Old Harbor Distilling Co, 1500 Distillery Rd, Bardstown KY"),
        _application_data(),
    )
    assert _field(report, "name_address").status == MatchStatus.MATCH


def test_name_address_no_match():
    report = engine.compare(
        _extracted_fields(name_address="456 Industrial Blvd, Nowhere, TX 75001"),
        _application_data(),
    )
    assert _field(report, "name_address").status == MatchStatus.NO_MATCH


# --- Country of Origin (fuzzy, >= 90% match / >= 70% partial) -----------------


def test_country_of_origin_partial_match():
    report = engine.compare(
        _extracted_fields(country_of_origin="United States of America"),
        _application_data(country_of_origin="United States"),
    )
    assert _field(report, "country_of_origin").status == MatchStatus.PARTIAL_MATCH


def test_country_of_origin_no_match():
    report = engine.compare(
        _extracted_fields(country_of_origin="France"),
        _application_data(country_of_origin="United States"),
    )
    assert _field(report, "country_of_origin").status == MatchStatus.NO_MATCH


# --- Missing OCR fields (SI-10: degrade gracefully, never raise) --------------


def test_all_fields_missing_from_ocr_is_overall_fail():
    extracted = _extracted_fields(
        brand=None,
        class_type=None,
        abv=None,
        net_contents=None,
        name_address=None,
        country_of_origin=None,
    )

    report = engine.compare(extracted, _application_data())

    assert report.overall_status == OverallStatus.FAIL
    assert all(f.status == MatchStatus.NO_MATCH for f in report.fields)
    assert all(f.score == 0.0 for f in report.fields)
    assert all(f.extracted is None for f in report.fields)
