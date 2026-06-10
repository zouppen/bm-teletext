from datetime import datetime, timezone

from dmr_teletext.page_data import (
    DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
    PAGE_ENTRY_LIMIT,
    LastHeardRow,
    build_page,
    has_bit_errors,
    is_usable_rssi,
    payload_to_entry,
    process_row,
)


def test_payload_to_entry_extracts_display_fields() -> None:
    received_at = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    entry = payload_to_entry(
        received_at,
        {
            "SourceCall": "OH2DPN",
            "SourceName": "Nick",
            "ContextID": 244200,
            "LinkCall": "OH2DMRH Pasila",
            "DestinationID": 2442,
            "RSSI": -112.3,
            "BER": 0,
        },
    )

    assert entry == {
        "received_at": "2026-06-10T12:00:00+00:00",
        "callsign": "OH2DPN",
        "name": "Nick",
        "repeater_id": "244200",
        "repeater": "OH2DMRH Pasila",
        "tg": "2442",
        "rssi": -112.3,
        "be": False,
    }


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


def test_process_row_appends_until_page_limit() -> None:
    entries_by_callsign = {}

    for index in range(PAGE_ENTRY_LIMIT - 1):
        row = LastHeardRow(
            received_at=datetime(2026, 6, 10, 12, index, tzinfo=timezone.utc),
            payload={"SourceCall": f"OH2{index:03d}", "ContextID": "244200"},
        )
        assert not process_row(entries_by_callsign, row)

    row = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, PAGE_ENTRY_LIMIT, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2LAST", "ContextID": "244200"},
    )
    assert process_row(entries_by_callsign, row)
    assert len(entries_by_callsign) == PAGE_ENTRY_LIMIT

    assert process_row(entries_by_callsign, row)
    assert len(entries_by_callsign) == PAGE_ENTRY_LIMIT


def test_process_row_skips_duplicate_and_empty_callsigns() -> None:
    entries_by_callsign = {}
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

    assert not process_row(entries_by_callsign, first)
    assert not process_row(entries_by_callsign, duplicate)
    assert not process_row(entries_by_callsign, empty)

    assert len(entries_by_callsign) == 1
    assert entries_by_callsign["OH2DPN"][1]["repeater_id"] == "244200"


def test_process_row_repairs_duplicate_rssi_and_ber_from_same_repeater() -> None:
    entries_by_callsign = {}
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

    assert not process_row(entries_by_callsign, first)
    assert not process_row(entries_by_callsign, duplicate)

    entry = entries_by_callsign["OH2DPN"][1]
    assert entry == {
        "received_at": "2026-06-10T12:00:00+00:00",
        "callsign": "OH2DPN",
        "name": "Nick",
        "repeater_id": "244200",
        "repeater": "OH2DMRH Pasila",
        "tg": "2442",
        "rssi": -112.3,
        "be": True,
    }


def test_process_row_does_not_repair_rssi_from_different_repeater() -> None:
    entries_by_callsign = {}
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": 0},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244201", "RSSI": -112.3},
    )

    assert not process_row(entries_by_callsign, first)
    assert not process_row(entries_by_callsign, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["rssi"] == 0


def test_process_row_does_not_repair_usable_rssi() -> None:
    entries_by_callsign = {}
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -100.0},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -112.3},
    )

    assert not process_row(entries_by_callsign, first)
    assert not process_row(entries_by_callsign, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["rssi"] == -100.0


def test_process_row_does_not_repair_from_unusable_rssi() -> None:
    entries_by_callsign = {}
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": None},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": "bad"},
    )

    assert not process_row(entries_by_callsign, first)
    assert not process_row(entries_by_callsign, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["rssi"] is None


def test_process_row_repairs_rssi_at_default_window_boundary() -> None:
    entries_by_callsign = {}
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": None},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 55, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -112.3},
    )

    assert DEFAULT_RSSI_REPAIR_WINDOW_SECONDS == 300
    assert not process_row(entries_by_callsign, first)
    assert not process_row(entries_by_callsign, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["rssi"] == -112.3


def test_process_row_does_not_repair_rssi_outside_default_window() -> None:
    entries_by_callsign = {}
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": None},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 54, 59, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -112.3},
    )

    assert not process_row(entries_by_callsign, first)
    assert not process_row(entries_by_callsign, duplicate)

    assert entries_by_callsign["OH2DPN"][1]["rssi"] is None


def test_process_row_uses_custom_repair_window() -> None:
    entries_by_callsign = {}
    first = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": None},
    )
    duplicate = LastHeardRow(
        received_at=datetime(2026, 6, 10, 11, 59, 30, tzinfo=timezone.utc),
        payload={"SourceCall": "OH2DPN", "ContextID": "244200", "RSSI": -112.3},
    )

    assert not process_row(entries_by_callsign, first, repair_window_seconds=29)
    assert not process_row(entries_by_callsign, duplicate, repair_window_seconds=29)

    assert entries_by_callsign["OH2DPN"][1]["rssi"] is None


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

    page = build_page(rows)

    assert len(page["entries"]) == PAGE_ENTRY_LIMIT
    assert page["row_count"] == PAGE_ENTRY_LIMIT
    assert len({entry["callsign"] for entry in page["entries"]}) == PAGE_ENTRY_LIMIT


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

    assert page["entries"] == [
        {
            "received_at": "2026-06-10T12:00:00+00:00",
            "callsign": "OH2DPN",
            "name": None,
            "repeater_id": "244200",
            "repeater": None,
            "tg": None,
            "rssi": None,
            "be": False,
        }
    ]


def test_build_page_sorts_entries_by_received_at_newest_first() -> None:
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

    assert [entry["callsign"] for entry in page["entries"]] == [
        "OH2NEW",
        "OH2MID",
        "OH2OLD",
    ]


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

    assert [entry["callsign"] for entry in page["entries"]] == ["OH2DPN", "OH2ABC"]
    assert page["entries"][0]["received_at"] == "2026-06-10T12:00:00+00:00"
    assert page["entries"][0]["rssi"] == -112.3
