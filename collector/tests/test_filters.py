import pytest

from bm_teletext_collector.filters import (
    ContextIdFilter,
    context_id_to_string,
    is_finnish_repeater_event,
)


def test_converts_context_ids_to_plain_strings() -> None:
    assert context_id_to_string(244123) == "244123"
    assert context_id_to_string("244123") == "244123"
    assert context_id_to_string(" 244123 ") == " 244123 "
    assert context_id_to_string("0244123") == "0244123"
    assert context_id_to_string(244123.0) == "244123.0"


def test_rejects_missing_context_id() -> None:
    assert context_id_to_string(None) is None
    assert is_finnish_repeater_event({}) is False


def test_default_filter_accepts_context_ids_starting_with_244() -> None:
    assert is_finnish_repeater_event({"ContextID": 244})
    assert is_finnish_repeater_event({"ContextID": 244000})
    assert is_finnish_repeater_event({"ContextID": 244205})
    assert is_finnish_repeater_event({"ContextID": "244999"})
    assert is_finnish_repeater_event({"ContextID": 2441234})


def test_default_filter_rejects_context_ids_not_starting_with_244() -> None:
    assert not is_finnish_repeater_event({"ContextID": 243999})
    assert not is_finnish_repeater_event({"ContextID": 245000})
    assert not is_finnish_repeater_event({"ContextID": "0244205"})


def test_default_filter_uses_search_semantics() -> None:
    assert ContextIdFilter(r"^244").matches_payload({"ContextID": 244205})
    assert ContextIdFilter(r"420").matches_payload({"ContextID": 244205})


def test_default_filter_does_not_canonicalize_padded_or_float_values() -> None:
    assert not is_finnish_repeater_event({"ContextID": "0244123"})
    assert not is_finnish_repeater_event({"ContextID": " 244123 "})
    assert is_finnish_repeater_event({"ContextID": 244123.0})


def test_default_filter_ignores_source_id() -> None:
    assert is_finnish_repeater_event({"ContextID": 244123, "SourceID": 9999999})
    assert not is_finnish_repeater_event({"ContextID": 9999999, "SourceID": 244123})


def test_custom_filter_pattern_is_supported() -> None:
    context_filter = ContextIdFilter(r"^999")

    assert context_filter.matches_payload({"ContextID": 999123})
    assert not context_filter.matches_payload({"ContextID": 244123})


def test_invalid_filter_pattern_fails_fast() -> None:
    with pytest.raises(Exception):
        ContextIdFilter("[")
