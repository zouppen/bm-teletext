from datetime import datetime, timezone

from dmr_teletext.page_data import (
    PAGE_ENTRY_LIMIT,
    LastHeardRow,
    build_page,
    has_bit_errors,
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
