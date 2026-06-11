import os
import time
from datetime import datetime, timezone

import pytest

from dmr_teletext.page_data import (
    DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
    PAGE_ENTRY_LIMIT,
    LastHeardRow,
    build_page,
    has_bit_errors,
    is_usable_rssi,
    local_day_marker_time,
    row_to_heard_entry,
    prepare_row_addition,
    timeline_entry_count,
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


def heard_entries(page):
    return [entry for entry in page["entries"] if entry["type"] == "heard"]


def day_entries(page):
    return [entry for entry in page["entries"] if entry["type"] == "day"]


def apply_row_addition(
    entries_by_callsign,
    days,
    row,
    repair_window_seconds=DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
):
    addition = prepare_row_addition(
        entries_by_callsign,
        row,
        repair_window_seconds,
    )
    if addition is not None:
        callsign, entry = addition
        entry_time = datetime.fromisoformat(entry["time"])
        days.add(local_day_marker_time(entry_time))
        entries_by_callsign[callsign] = (entry_time, entry)
    return addition


def test_row_to_heard_entry_copies_payload() -> None:
    payload = {
        "SourceCall": "OH2DPN",
        "SourceName": "Nick",
        "ContextID": 244200,
        "LinkCall": "OH2DMRH Pasila",
        "DestinationID": 2442,
        "RSSI": -112.3,
        "BER": 0,
    }
    row = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload=payload,
    )

    entry = row_to_heard_entry(row)

    assert entry == {
        "type": "heard",
        "time": "2026-06-10T12:00:00+00:00",
        "payload": payload,
    }
    assert entry["payload"] is not payload


def test_row_to_heard_entry_omits_repaired_by_default() -> None:
    row = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN"},
    )

    entry = row_to_heard_entry(
        row,
    )

    assert "repaired" not in entry


def test_has_bit_errors() -> None:
    assert not has_bit_errors(None)
    assert not has_bit_errors(0)
    assert not has_bit_errors("0")
    assert has_bit_errors(1)
    assert has_bit_errors("0.1")
    assert has_bit_errors("bad")


def test_is_usable_rssi() -> None:
    assert not is_usable_rssi(None)
    assert not is_usable_rssi("bad")
    assert not is_usable_rssi(0)
    assert not is_usable_rssi("0")
    assert not is_usable_rssi(1)
    assert not is_usable_rssi("1")
    assert is_usable_rssi(-1)
    assert is_usable_rssi(-112.3)
    assert is_usable_rssi("-112.3")


def test_local_day_marker_time_uses_system_timezone(set_timezone) -> None:
    set_timezone("Europe/Helsinki")

    day = local_day_marker_time(datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc))

    assert day.isoformat() == "2026-06-11T00:00:00+03:00"


def test_local_day_marker_time_maps_utc_boundary_to_local_day(set_timezone) -> None:
    set_timezone("Europe/Helsinki")

    day = local_day_marker_time(datetime(2026, 6, 9, 21, 30, tzinfo=timezone.utc))

    assert day.isoformat() == "2026-06-11T00:00:00+03:00"


def test_local_day_marker_time_treats_naive_datetime_as_utc(set_timezone) -> None:
    set_timezone("UTC")

    day = local_day_marker_time(datetime(2026, 6, 10, 12, 0))

    assert day.isoformat() == "2026-06-11T00:00:00+00:00"


def test_timeline_entry_count_excludes_newest_day_marker(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    entries_by_callsign = {
        "OH2DPN": (
            datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
            row_to_heard_entry(
                LastHeardRow(
                    received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
                    payload={"SourceCall": "OH2DPN"},
                )
            ),
        )
    }
    days = {
        local_day_marker_time(datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)),
        local_day_marker_time(datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)),
    }

    assert timeline_entry_count(entries_by_callsign, days) == 2


def test_timeline_entry_count_handles_empty_days() -> None:
    assert timeline_entry_count({}, set()) == 0


def test_prepare_row_addition_appends_until_page_limit() -> None:
    entries_by_callsign = {}
    days = set()

    for index in range(PAGE_ENTRY_LIMIT - 1):
        row = LastHeardRow(
            received_at=datetime(2026, 6, 10, 12, index, tzinfo=timezone.utc),
            payload={"SourceCall": f"OH2{index:03d}", "ContextID": "244200"},
        )
        apply_row_addition(entries_by_callsign, days, row)

    row = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, PAGE_ENTRY_LIMIT, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2LAST", "ContextID": "244200"},
    )
    apply_row_addition(entries_by_callsign, days, row)
    assert len(entries_by_callsign) == PAGE_ENTRY_LIMIT

    apply_row_addition(entries_by_callsign, days, row)
    assert len(entries_by_callsign) == PAGE_ENTRY_LIMIT


def test_prepare_row_addition_skips_duplicate_and_empty_callsigns() -> None:
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200"},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244201"},
    )
    empty = LastHeardRow(
        received_at=datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "", "ContextID": "244202"},
    )

    assert apply_row_addition(entries_by_callsign, days, first) is not None
    assert not apply_row_addition(entries_by_callsign, days, duplicate)
    assert not apply_row_addition(entries_by_callsign, days, empty)

    assert len(entries_by_callsign) == 1
    assert entries_by_callsign["OH2DPN"][1]["payload"]["ContextID"] == "244200"


def test_prepare_row_addition_adds_day_for_new_callsign(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    entries_by_callsign = {}
    days = set()
    row = LastHeardRow(
        received_at=datetime(2026, 6, 9, 21, 30, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200"},
    )

    addition = apply_row_addition(entries_by_callsign, days, row)

    assert addition is not None
    callsign, entry = addition
    assert callsign == "OH2DPN"
    assert entry["payload"]["ContextID"] == "244200"
    assert {day.isoformat() for day in days} == {"2026-06-11T00:00:00+03:00"}


def test_prepare_row_addition_returns_data_without_storing_it(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    entries_by_callsign = {}
    row = LastHeardRow(
        received_at=datetime(2026, 6, 9, 21, 30, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200"},
    )

    addition = prepare_row_addition(entries_by_callsign, row)

    assert addition is not None
    callsign, entry = addition
    assert callsign == "OH2DPN"
    assert entry["payload"]["ContextID"] == "244200"
    assert entries_by_callsign == {}


def test_prepare_row_addition_does_not_add_day_for_skipped_rows(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200"},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 9, 21, 30, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200"},
    )
    empty = LastHeardRow(
        received_at=datetime(2026, 6, 8, 21, 30, tzinfo=timezone.utc),
        payload={"SourceCall": "", "ContextID": "244201"},
    )

    assert apply_row_addition(entries_by_callsign, days, first) is not None
    assert not apply_row_addition(entries_by_callsign, days, duplicate)
    assert not apply_row_addition(entries_by_callsign, days, empty)

    assert {day.isoformat() for day in days} == {"2026-06-11T00:00:00+03:00"}


def test_prepare_row_addition_repairs_duplicate_rssi_and_ber_from_same_repeater() -> None:
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={
            "SourceCall": "OH2DPN",
            "SourceName": "Nick",
            "ContextID": "244200",
            "LinkCall": "OH2DMRH Pasila",
            "DestinationID": 2442,
            "RSSI": 0,
            "BER": 0,
        },
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 57, tzinfo=timezone.utc),
        payload={
            "SourceCall": "OH2DPN",
            "SourceName": "Older",
            "ContextID": "244200",
            "LinkCall": "Older repeater name",
            "DestinationID": 2443,
            "RSSI": -112.3,
            "BER": "0.1",
        },
    )

    first_addition = apply_row_addition(entries_by_callsign, days, first)
    assert first_addition is not None
    stored_entry_before = entries_by_callsign["OH2DPN"][1]

    repair_addition = apply_row_addition(entries_by_callsign, days, duplicate)
    assert repair_addition is not None

    entry = entries_by_callsign["OH2DPN"][1]
    assert entry == {
        "type": "heard",
        "time": "2026-06-10T12:00:00+00:00",
        "payload": {
            "SourceCall": "OH2DPN",
            "SourceName": "Nick",
            "ContextID": "244200",
            "LinkCall": "OH2DMRH Pasila",
            "DestinationID": 2442,
            "RSSI": -112.3,
            "BER": "0.1",
        },
        "repaired": True,
    }
    assert stored_entry_before["payload"]["RSSI"] == 0
    assert "repaired" not in stored_entry_before
    assert first.payload["RSSI"] == 0
    assert first.payload["BER"] == 0
    assert duplicate.payload["RSSI"] == -112.3
    assert duplicate.payload["BER"] == "0.1"


def test_prepare_row_addition_does_not_repair_rssi_from_different_repeater() -> None:
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": 0},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244201", "RSSI": -112.3},
    )

    assert apply_row_addition(entries_by_callsign, days, first) is not None
    assert not apply_row_addition(entries_by_callsign, days, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["payload"].get("RSSI") == 0


def test_prepare_row_addition_does_not_repair_usable_rssi() -> None:
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -100.0},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -112.3},
    )

    assert apply_row_addition(entries_by_callsign, days, first) is not None
    assert not apply_row_addition(entries_by_callsign, days, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["payload"].get("RSSI") == -100.0


def test_prepare_row_addition_does_not_repair_from_unusable_rssi() -> None:
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": None},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": "bad"},
    )

    assert apply_row_addition(entries_by_callsign, days, first) is not None
    assert not apply_row_addition(entries_by_callsign, days, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["payload"].get("RSSI") is None


def test_prepare_row_addition_repairs_rssi_at_default_window_boundary() -> None:
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": None},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 55, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -112.3},
    )

    assert DEFAULT_RSSI_REPAIR_WINDOW_SECONDS == 300
    assert apply_row_addition(entries_by_callsign, days, first) is not None
    assert apply_row_addition(entries_by_callsign, days, duplicate) is not None

    assert entries_by_callsign["OH2DPN"][1]["payload"].get("RSSI") == -112.3


def test_prepare_row_addition_does_not_repair_rssi_outside_default_window() -> None:
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": None},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 54, 59, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -112.3},
    )

    assert apply_row_addition(entries_by_callsign, days, first) is not None
    assert not apply_row_addition(entries_by_callsign, days, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["payload"].get("RSSI") is None


def test_prepare_row_addition_uses_custom_repair_window() -> None:
    entries_by_callsign = {}
    days = set()
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": None},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 59, 30, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -112.3},
    )

    assert (
        apply_row_addition(entries_by_callsign, days, first, repair_window_seconds=29)
        is not None
    )
    assert not apply_row_addition(
        entries_by_callsign,
        days,
        duplicate,
        repair_window_seconds=29,
    )

    assert entries_by_callsign["OH2DPN"][1]["payload"].get("RSSI") is None


def test_build_page_collects_unique_callsigns_until_limit() -> None:
    rows = (
        LastHeardRow(
            received_at=datetime(2026, 6, 10, 12, minute, tzinfo=timezone.utc),
            payload={
                "SourceCall": "DUPLICATE" if minute % 2 else f"OH2{minute:03d}",
                "ContextID": 244000 + minute,
            },
        )
        for minute in range(PAGE_ENTRY_LIMIT * 2 + 1)
    )

    page = build_page(
        rows,
        page_time=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
    )

    heard = heard_entries(page)
    assert len(heard) == PAGE_ENTRY_LIMIT
    assert page["heard_count"] == PAGE_ENTRY_LIMIT
    assert len({entry["payload"].get("SourceCall") for entry in heard}) == PAGE_ENTRY_LIMIT


def test_build_page_single_day_limit_ignores_dropped_day_marker(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    rows = (
        LastHeardRow(
            received_at=datetime(2026, 6, 10, 12, minute, tzinfo=timezone.utc),
            payload={"SourceCall": f"OH2{minute:03d}", "ContextID": "244200"},
        )
        for minute in range(PAGE_ENTRY_LIMIT + 1)
    )

    page = build_page(
        rows,
        page_time=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
    )

    assert len(page["entries"]) == PAGE_ENTRY_LIMIT
    assert len(heard_entries(page)) == PAGE_ENTRY_LIMIT
    assert day_entries(page) == []


def test_build_page_counts_printed_day_markers_against_limit(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    rows = (
        LastHeardRow(
            received_at=datetime(2026, 6, 10, 12, minute, tzinfo=timezone.utc),
            payload={"SourceCall": f"OH2NEW{minute:03d}", "ContextID": "244200"},
        )
        for minute in range(PAGE_ENTRY_LIMIT - 2)
    )
    rows = iter(
        [
            *rows,
            LastHeardRow(
                received_at=datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2OLD", "ContextID": "244200"},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2TOOOLD", "ContextID": "244200"},
            ),
        ]
    )

    page = build_page(
        rows,
        page_time=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
    )

    assert len(page["entries"]) == PAGE_ENTRY_LIMIT
    assert len(heard_entries(page)) == PAGE_ENTRY_LIMIT - 1
    assert [entry["time"] for entry in day_entries(page)] == [
        "2026-06-10T00:00:00+03:00"
    ]
    callsigns = {entry["payload"].get("SourceCall") for entry in heard_entries(page)}
    assert "OH2OLD" in callsigns
    assert "OH2TOOOLD" not in callsigns


def test_build_page_drops_day_marker_that_would_end_truncated_page(
    set_timezone,
) -> None:
    set_timezone("Europe/Helsinki")
    rows = (
        LastHeardRow(
            received_at=datetime(2026, 6, 10, 12, minute, tzinfo=timezone.utc),
            payload={"SourceCall": f"OH2NEW{minute:03d}", "ContextID": "244200"},
        )
        for minute in range(PAGE_ENTRY_LIMIT - 1)
    )
    rows = iter(
        [
            *rows,
            LastHeardRow(
                received_at=datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2OLD", "ContextID": "244200"},
            ),
        ]
    )

    page = build_page(
        rows,
        page_time=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
    )

    assert len(page["entries"]) == PAGE_ENTRY_LIMIT - 1
    assert page["entries"][-1]["type"] == "heard"
    callsigns = {entry["payload"].get("SourceCall") for entry in heard_entries(page)}
    assert "OH2OLD" not in callsigns


def test_build_page_removes_trailing_day_marker(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    rows = iter(
        [
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2DPN", "ContextID": "244200"},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "", "ContextID": "244201"},
            ),
        ]
    )

    page = build_page(
        rows,
        page_time=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
    )

    assert page["entries"][-1]["type"] == "heard"
    assert {entry["time"] for entry in day_entries(page)} == {
        "2026-06-11T00:00:00+03:00"
    }


def test_build_page_includes_page_time_day_when_no_rows(set_timezone) -> None:
    set_timezone("Europe/Helsinki")

    page = build_page(
        iter(()),
        page_time=datetime(2026, 6, 9, 21, 30, tzinfo=timezone.utc),
    )

    assert page["entries"] == []
    assert page["heard_count"] == 0
    assert "row_count" not in page
    assert "days" not in page


def test_build_page_collects_days_from_accepted_entries(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    rows = iter(
        [
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2DPN", "ContextID": 244200},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 9, 21, 30, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2ABC", "ContextID": 244201},
            ),
        ]
    )

    page = build_page(
        rows,
        page_time=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
    )

    assert {entry["time"] for entry in day_entries(page)} == {
        "2026-06-11T00:00:00+03:00",
    }
    assert page["heard_count"] == 2


def test_build_page_keeps_newest_row_for_callsign() -> None:
    rows = iter(
        [
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2DPN", "ContextID": 244200},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2DPN", "ContextID": 244201},
            ),
        ]
    )

    page = build_page(rows)

    assert heard_entries(page) == [
        {
            "type": "heard",
            "time": "2026-06-10T12:00:00+00:00",
            "payload": {"SourceCall": "OH2DPN", "ContextID": 244200},
        }
    ]


def test_build_page_sorts_entries_by_time_newest_first() -> None:
    rows = iter(
        [
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2OLD", "ContextID": 244200},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2NEW", "ContextID": 244201},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2MID", "ContextID": 244202},
            ),
        ]
    )

    page = build_page(rows)

    assert [entry["payload"].get("SourceCall") for entry in heard_entries(page)] == [
        "OH2NEW",
        "OH2MID",
        "OH2OLD",
    ]


def test_build_page_sorts_heard_entries_and_days_together(set_timezone) -> None:
    set_timezone("Europe/Helsinki")
    rows = iter(
        [
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 20, 59, 59, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2LATE", "ContextID": 244200},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 9, 21, 30, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2NEW_DAY", "ContextID": 244201},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2MID_DAY", "ContextID": 244202},
            ),
        ]
    )

    page = build_page(
        rows,
        page_time=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
    )

    assert [
        (entry["type"], entry["time"]) for entry in page["entries"]
    ] == [
        ("day", "2026-06-11T00:00:00+03:00"),
        ("heard", "2026-06-10T20:59:59+00:00"),
        ("heard", "2026-06-10T10:00:00+00:00"),
        ("heard", "2026-06-09T21:30:00+00:00"),
    ]
    assert page["heard_count"] == 3


def test_build_page_preserves_ordering_after_rssi_repair() -> None:
    rows = iter(
        [
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2DPN", "ContextID": 244200, "RSSI": 0},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2ABC", "ContextID": 244201},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 11, 56, tzinfo=timezone.utc),
                payload={
                    "SourceCall": "OH2DPN",
                    "ContextID": 244200,
                    "RSSI": -112.3,
                },
            ),
        ]
    )

    page = build_page(rows)

    heard = heard_entries(page)
    assert [entry["payload"].get("SourceCall") for entry in heard] == [
        "OH2DPN",
        "OH2ABC",
    ]
    assert heard[0]["time"] == "2026-06-10T12:00:00+00:00"
    assert heard[0]["payload"].get("RSSI") == -112.3


def test_build_page_uses_selected_entry_time_for_repaired_day_marker(
    set_timezone,
) -> None:
    set_timezone("Europe/Helsinki")
    rows = iter(
        [
            LastHeardRow(
                received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
                payload={"SourceCall": "OH2DPN", "ContextID": 244200, "RSSI": 0},
            ),
            LastHeardRow(
                received_at=datetime(2026, 6, 9, 20, 58, tzinfo=timezone.utc),
                payload={
                    "SourceCall": "OH2DPN",
                    "ContextID": 244200,
                    "RSSI": -112.3,
                    "BER": "0.1",
                },
            ),
        ]
    )

    page = build_page(
        rows,
        page_time=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
        repair_window_seconds=86_400,
    )

    assert [entry["time"] for entry in day_entries(page)] == [
        "2026-06-11T00:00:00+03:00"
    ]
    heard = heard_entries(page)
    assert heard == [
        {
            "type": "heard",
            "time": "2026-06-10T12:00:00+00:00",
            "payload": {
                "SourceCall": "OH2DPN",
                "ContextID": 244200,
                "RSSI": -112.3,
                "BER": "0.1",
            },
            "repaired": True,
        }
    ]
