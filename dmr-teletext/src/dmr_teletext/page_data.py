from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypedDict


PAGE_ENTRY_LIMIT = 20
DEFAULT_RSSI_REPAIR_WINDOW_SECONDS = 300


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
    days: list[str]
    entries: list[PageEntry]


EntryByCallsign = dict[str, tuple[datetime, PageEntry]]
DaySet = set[datetime]


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
        "days": [],
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


def is_usable_rssi(value: Any) -> bool:
    try:
        return float(value) < 0.0
    except (TypeError, ValueError):
        return False


def local_midnight(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local_value = value.astimezone()
    return local_value.replace(hour=0, minute=0, second=0, microsecond=0)


def repair_signal_quality(
    stored_received_at: datetime,
    stored_entry: PageEntry,
    duplicate_received_at: datetime,
    duplicate_entry: PageEntry,
    repair_window_seconds: int = DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
) -> None:
    age_seconds = (stored_received_at - duplicate_received_at).total_seconds()
    if age_seconds > repair_window_seconds:
        return
    if stored_entry["repeater_id"] != duplicate_entry["repeater_id"]:
        return
    if is_usable_rssi(stored_entry["rssi"]):
        return
    if not is_usable_rssi(duplicate_entry["rssi"]):
        return

    stored_entry["rssi"] = duplicate_entry["rssi"]
    stored_entry["be"] = duplicate_entry["be"]


def process_row(
    entries_by_callsign: EntryByCallsign,
    days: DaySet,
    row: LastHeardRow,
    repair_window_seconds: int = DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
) -> bool:
    if len(entries_by_callsign) >= PAGE_ENTRY_LIMIT:
        return True

    entry = payload_to_entry(row.received_at, row.payload)
    callsign = entry["callsign"]
    if not callsign:
        return False
    if callsign in entries_by_callsign:
        stored_received_at, stored_entry = entries_by_callsign[callsign]
        repair_signal_quality(
            stored_received_at,
            stored_entry,
            row.received_at,
            entry,
            repair_window_seconds,
        )
        return False

    entries_by_callsign[callsign] = (row.received_at, entry)
    days.add(local_midnight(row.received_at))
    return len(entries_by_callsign) >= PAGE_ENTRY_LIMIT


def build_page(
    rows: Iterator[LastHeardRow],
    repair_window_seconds: int = DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
    generated_at: datetime | None = None,
) -> PageData:
    page = create_page(generated_at)
    entries_by_callsign: EntryByCallsign = {}
    days = {local_midnight(datetime.fromisoformat(page["generated_at"]))}

    for row in rows:
        if process_row(entries_by_callsign, days, row, repair_window_seconds):
            break

    page["entries"] = [
        entry
        for _, entry in sorted(
            entries_by_callsign.values(), key=lambda item: item[0], reverse=True
        )
    ]
    page["row_count"] = len(page["entries"])
    page["days"] = [day.isoformat() for day in days]
    return page
