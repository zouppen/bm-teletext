import os
import time

import pytest

from dmr_teletext.text_format import (
    LINE_WIDTH,
    format_entry,
    format_header,
    format_page_ep1,
    format_page_text,
    format_rssi,
)


@pytest.fixture
def set_timezone(monkeypatch):
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset is required to test local timezone behavior")

    original_tz = os.environ.get("TZ")

    def apply(value: str) -> None:
        monkeypatch.setenv("TZ", value)
        time.tzset()

    yield apply

    if original_tz is None:
        monkeypatch.delenv("TZ", raising=False)
    else:
        monkeypatch.setenv("TZ", original_tz)
    time.tzset()


def heard_entry(**overrides):
    entry = {
        "type": "heard",
        "time": "2026-06-10T12:34:00+00:00",
        "payload": {
            "SourceCall": "OH2DPN",
            "SourceName": "Nick",
            "ContextID": "244200",
            "LinkCall": "OH2DMRH Pasila",
            "DestinationID": "2442",
            "RSSI": -109.3,
            "BER": 0,
        },
    }
    aliases = {
        "callsign": "SourceCall",
        "repeater": "LinkCall",
        "rssi": "RSSI",
        "be": "BER",
    }
    payload_overrides = overrides.pop("payload", {})
    entry["payload"].update(payload_overrides)
    for key, value in overrides.items():
        entry["payload"][aliases.get(key, key)] = value
    return entry


def test_format_header_is_fixed_width() -> None:
    assert format_header() == "AIKA  KUTSU    TOISTIN            RSSI B"
    assert len(format_header()) == LINE_WIDTH


def test_format_heard_entry_uses_fixed_width_columns(set_timezone) -> None:
    set_timezone("UTC")

    line = format_entry(heard_entry())

    assert line == "12:34 OH2DPN   OH2DMRH Pasila     -109  "
    assert len(line) == LINE_WIDTH


def test_format_heard_entry_truncates_repeater(set_timezone) -> None:
    set_timezone("UTC")

    line = format_entry(
        heard_entry(repeater="OH2DMRH Pasila Keskusta Long Extra")
    )

    assert line == "12:34 OH2DPN   OH2DMRH Pasila Kes -109  "
    assert len(line) == LINE_WIDTH


def test_format_heard_entry_truncates_long_callsign(set_timezone) -> None:
    set_timezone("UTC")

    line = format_entry(heard_entry(callsign="OH2VERYLONG"))

    assert line.startswith("12:34 OH2VERYL ")
    assert len(line) == LINE_WIDTH


def test_format_rssi_rounds_negative_values() -> None:
    assert format_rssi(-109.3) == "-109"
    assert format_rssi("-109.8") == "-110"


@pytest.mark.parametrize("value", [None, "bad", 0, "0", 1, "1"])
def test_format_rssi_suppresses_missing_zero_positive_or_bad_values(value) -> None:
    assert format_rssi(value) == ""


def test_format_heard_entry_aligns_bit_error_marker_with_rssi(set_timezone) -> None:
    set_timezone("UTC")

    with_rssi = format_entry(heard_entry(rssi=-109.3, be=True))
    without_rssi = format_entry(heard_entry(rssi=0, be=True))

    assert with_rssi == "12:34 OH2DPN   OH2DMRH Pasila     -109 *"
    assert without_rssi == "12:34 OH2DPN   OH2DMRH Pasila          *"
    assert with_rssi.index("*") == without_rssi.index("*") == LINE_WIDTH - 1


def test_format_page_ep1_colours_rssi_by_threshold(set_timezone) -> None:
    set_timezone("UTC")
    page = {
        "page_time": "2026-06-10T12:34:00+00:00",
        "page_entry_limit": 1,
        "retained_callsign_count": 1,
        "rows_iterated": 1,
        "entries": [heard_entry(rssi=-89)],
    }

    green_output = format_page_ep1(page, subpage="11/12", rssi_yellow_threshold=-90)
    yellow_output = format_page_ep1(page, subpage="11/12", rssi_yellow_threshold=-88)

    assert b"\x02 -89\x01" in green_output
    assert b"\x03 -89\x01" in yellow_output


def test_format_heard_entry_handles_missing_repeater(set_timezone) -> None:
    set_timezone("UTC")

    line = format_entry(heard_entry(repeater=None, rssi=None, be=False))

    assert line == "12:34 OH2DPN                            "
    assert len(line) == LINE_WIDTH


def test_format_day_entry_uses_previous_local_date(set_timezone) -> None:
    set_timezone("Europe/Helsinki")

    line = format_entry({"type": "day", "time": "2026-06-11T00:00:00+03:00"})

    assert line == "2026-06-10"


def test_format_day_entry_uses_previous_date_after_local_conversion(
    set_timezone,
) -> None:
    set_timezone("Europe/Helsinki")

    line = format_entry({"type": "day", "time": "2026-06-10T21:00:00+00:00"})

    assert line == "2026-06-10"


def test_format_page_text_includes_header() -> None:
    page = {
        "page_time": "2026-06-10T12:34:00+00:00",
        "page_entry_limit": 20,
        "retained_callsign_count": 0,
        "rows_iterated": 0,
        "entries": [],
    }

    assert format_page_text(page) == format_header()
