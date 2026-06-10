from datetime import datetime, timezone

from dmr_teletext.page_data import (
    PAGE_ENTRY_LIMIT,
    LastHeardRow,
    build_page,
    create_page,
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
    page = create_page(datetime(2026, 6, 10, tzinfo=timezone.utc))
    row = LastHeardRow(
        received_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        payload={"ContextID": "244200"},
    )

    for _ in range(PAGE_ENTRY_LIMIT - 1):
        assert not process_row(page, row)

    assert process_row(page, row)
    assert len(page["entries"]) == PAGE_ENTRY_LIMIT
    assert page["row_count"] == PAGE_ENTRY_LIMIT

    assert process_row(page, row)
    assert len(page["entries"]) == PAGE_ENTRY_LIMIT


def test_build_page_preserves_input_order_and_stops_at_limit() -> None:
    rows = (
        LastHeardRow(
            received_at=datetime(2026, 6, 10, 12, minute, tzinfo=timezone.utc),
            payload={"ContextID": 244000 + minute},
        )
        for minute in range(PAGE_ENTRY_LIMIT + 5)
    )

    page = build_page(rows)

    assert len(page["entries"]) == PAGE_ENTRY_LIMIT
    assert page["entries"][0]["repeater_id"] == "244000"
    assert page["entries"][-1]["repeater_id"] == f"244{PAGE_ENTRY_LIMIT - 1:03d}"
