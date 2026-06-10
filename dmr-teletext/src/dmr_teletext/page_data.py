from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypedDict


PAGE_ENTRY_LIMIT = 20


class PageEntry(TypedDict):
    received_at: str
    callsign: str | None
    name: str | None
    repeater_id: str | None
    repeater: str | None
    tg: str | None
    rssi: Any
    be: bool


class PageData(TypedDict):
    generated_at: str
    page_entry_limit: int
    row_count: int
    entries: list[PageEntry]


@dataclass(frozen=True)
class LastHeardRow:
    received_at: datetime
    payload: Mapping[str, Any]


def create_page(generated_at: datetime | None = None) -> PageData:
    generated_at = generated_at or datetime.now(timezone.utc)
    return {
        "generated_at": generated_at.isoformat(),
        "page_entry_limit": PAGE_ENTRY_LIMIT,
        "row_count": 0,
        "entries": [],
    }


def payload_to_entry(received_at: datetime, payload: Mapping[str, Any]) -> PageEntry:
    return {
        "received_at": received_at.isoformat(),
        "callsign": payload_text(payload, "SourceCall"),
        "name": payload_text(payload, "SourceName"),
        "repeater_id": payload_text(payload, "ContextID"),
        "repeater": payload_text(payload, "LinkCall"),
        "tg": payload_text(payload, "DestinationID"),
        "rssi": payload.get("RSSI"),
        "be": has_bit_errors(payload.get("BER")),
    }


def payload_text(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    return str(value)


def has_bit_errors(value: Any) -> bool:
    if value is None:
        return False

    try:
        return float(value) != 0.0
    except (TypeError, ValueError):
        return bool(value)


def process_row(page: PageData, row: LastHeardRow) -> bool:
    if len(page["entries"]) >= PAGE_ENTRY_LIMIT:
        return True

    page["entries"].append(payload_to_entry(row.received_at, row.payload))
    page["row_count"] = len(page["entries"])
    return len(page["entries"]) >= PAGE_ENTRY_LIMIT


def build_page(rows: Iterator[LastHeardRow]) -> PageData:
    page = create_page()
    for row in rows:
        if process_row(page, row):
            break
    return page
