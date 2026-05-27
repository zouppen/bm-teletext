import pytest

from bm_teletext_collector.filters import (
    SourceIdFilter,
    is_finnish_repeater_event,
    parse_source_id,
    source_id_to_string,
)


def test_converts_source_ids_to_canonical_decimal_strings() -> None:
    assert source_id_to_string(244123) == "244123"
    assert source_id_to_string("244123") == "244123"
    assert source_id_to_string(" 244123 ") == "244123"
    assert source_id_to_string("0244123") == "244123"
    assert source_id_to_string(244123.0) == "244123"


def test_rejects_non_decimal_source_ids() -> None:
    assert source_id_to_string(None) is None
    assert source_id_to_string("not-a-number") is None
    assert source_id_to_string(244123.5) is None
    assert source_id_to_string(True) is None
    assert is_finnish_repeater_event({}) is False


def test_default_filter_accepts_six_digit_finnish_repeater_range() -> None:
    assert parse_source_id(244000) == 244000
    assert parse_source_id("244123") == 244123
    assert parse_source_id(244999) == 244999
    assert is_finnish_repeater_event({"SourceID": 244000})
    assert is_finnish_repeater_event({"SourceID": "244999"})


def test_default_filter_rejects_out_of_range_source_ids() -> None:
    assert parse_source_id(243999) == 243999
    assert not is_finnish_repeater_event({"SourceID": 243999})
    assert not is_finnish_repeater_event({"SourceID": 245000})


def test_default_filter_rejects_seven_digit_finnish_operator_style_ids() -> None:
    assert parse_source_id(2440000) == 2440000
    assert parse_source_id("2441234") == 2441234
    assert parse_source_id(2449999) == 2449999
    assert not is_finnish_repeater_event({"SourceID": 2441234})


def test_default_filter_matches_after_string_canonicalization() -> None:
    assert is_finnish_repeater_event({"SourceID": "0244123"})


def test_custom_filter_pattern_is_supported() -> None:
    source_filter = SourceIdFilter(r"^999\d{3}$")

    assert source_filter.matches_payload({"SourceID": 999123})
    assert not source_filter.matches_payload({"SourceID": 244123})


def test_invalid_filter_pattern_fails_fast() -> None:
    with pytest.raises(Exception):
        SourceIdFilter("[")
