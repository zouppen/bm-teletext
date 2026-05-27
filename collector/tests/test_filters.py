from bm_teletext_collector.filters import (
    is_finnish_repeater_event,
    parse_source_id,
)


def test_accepts_six_digit_finnish_repeater_range() -> None:
    assert parse_source_id(244000) == 244000
    assert parse_source_id("244123") == 244123
    assert parse_source_id(244999) == 244999


def test_rejects_out_of_range_source_ids() -> None:
    assert parse_source_id(243999) == 243999
    assert not is_finnish_repeater_event({"SourceID": 243999})
    assert not is_finnish_repeater_event({"SourceID": 245000})


def test_rejects_missing_or_non_numeric_source_ids() -> None:
    assert parse_source_id(None) is None
    assert parse_source_id("not-a-number") is None
    assert parse_source_id("") is None
    assert parse_source_id(True) is None
    assert not is_finnish_repeater_event({})


def test_rejects_seven_digit_finnish_operator_style_ids() -> None:
    assert parse_source_id(2440000) is None
    assert parse_source_id("2441234") is None
    assert parse_source_id(2449999) is None
    assert not is_finnish_repeater_event({"SourceID": 2441234})


def test_matches_only_finnish_repeater_source_ids() -> None:
    assert is_finnish_repeater_event({"SourceID": 244000})
    assert is_finnish_repeater_event({"SourceID": "244999"})
    assert not is_finnish_repeater_event({"SourceID": "0244123"})
