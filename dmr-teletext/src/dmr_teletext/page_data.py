from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, TypedDict


PAGE_ENTRY_LIMIT = 20
DEFAULT_RSSI_REPAIR_WINDOW_SECONDS = 300


class HeardEntry(TypedDict, total=False):
    type: Literal["heard"]
    time: str
    payload: dict[str, Any]
    repaired: bool


class DayEntry(TypedDict):
    type: Literal["day"]
    time: str


PageEntry = HeardEntry | DayEntry


class PageData(TypedDict):
    page_time: str
    page_entry_limit: int
    heard_count: int
    entries: list[PageEntry]


EntryByCallsign = dict[str, tuple[datetime, HeardEntry]]
DaySet = set[datetime]


@dataclass(frozen=True)
class LastHeardRow:
    received_at: datetime
    payload: Mapping[str, Any]


def create_page(page_time: datetime | None = None) -> PageData:
    page_time = page_time or datetime.now(timezone.utc)
    return {
        "page_time": page_time.isoformat(),
        "page_entry_limit": PAGE_ENTRY_LIMIT,
        "heard_count": 0,
        "entries": [],
    }


def row_to_heard_entry(row: LastHeardRow) -> HeardEntry:
    return {
        "type": "heard",
        "time": row.received_at.isoformat(),
        "payload": dict(row.payload),
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


def local_day_marker_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local_value = value.astimezone()
    local_midnight = local_value.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight + timedelta(days=1)


def timeline_entry_count(entries_by_callsign: EntryByCallsign, days: DaySet) -> int:
    return len(entries_by_callsign) + max(len(days) - 1, 0)


def repair_signal_quality(
    stored_received_at: datetime,
    stored_entry: HeardEntry,
    duplicate_received_at: datetime,
    duplicate_entry: HeardEntry,
    repair_window_seconds: int = DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
) -> HeardEntry | None:
    age_seconds = (stored_received_at - duplicate_received_at).total_seconds()
    if age_seconds > repair_window_seconds:
        return None
    if (
        payload_text(stored_entry["payload"], "ContextID")
        != payload_text(duplicate_entry["payload"], "ContextID")
    ):
        return None
    if is_usable_rssi(stored_entry["payload"].get("RSSI")):
        return None
    if not is_usable_rssi(duplicate_entry["payload"].get("RSSI")):
        return None

    repaired_entry = HeardEntry(stored_entry)
    repaired_entry["payload"] = dict(stored_entry["payload"])
    repaired_entry["payload"]["RSSI"] = duplicate_entry["payload"].get("RSSI")
    repaired_entry["payload"]["BER"] = duplicate_entry["payload"].get("BER")
    repaired_entry["repaired"] = True
    return repaired_entry


def prepare_row_addition(
    entries_by_callsign: EntryByCallsign,
    row: LastHeardRow,
    repair_window_seconds: int = DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
) -> tuple[str, HeardEntry] | None:
    entry = row_to_heard_entry(row)
    callsign = payload_text(entry["payload"], "SourceCall")
    if not callsign:
        return None
    if callsign in entries_by_callsign:
        stored_received_at, stored_entry = entries_by_callsign[callsign]
        repaired_entry = repair_signal_quality(
            stored_received_at,
            stored_entry,
            row.received_at,
            entry,
            repair_window_seconds,
        )
        if repaired_entry is None:
            return None
        return callsign, repaired_entry

    return callsign, entry


def build_page(
    rows: Iterator[LastHeardRow],
    repair_window_seconds: int = DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
    page_time: datetime | None = None,
) -> PageData:
    page = create_page(page_time)
    entries_by_callsign: EntryByCallsign = {}
    days = {local_day_marker_time(datetime.fromisoformat(page["page_time"]))}

    for row in rows:
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
        if timeline_entry_count(entries_by_callsign, days) >= PAGE_ENTRY_LIMIT:
            break

    heard_entries: list[PageEntry] = [
        entry
        for _, entry in entries_by_callsign.values()
    ]
    day_entries: list[PageEntry] = [
        {"type": "day", "time": day.isoformat()} for day in days
    ]
    page["entries"] = sorted(
        [*heard_entries, *day_entries],
        key=lambda item: datetime.fromisoformat(item["time"]),
        reverse=True,
    )
    if page["entries"] and page["entries"][0]["type"] == "day":
        page["entries"].pop(0)
    page["entries"] = page["entries"][:PAGE_ENTRY_LIMIT]
    if page["entries"] and page["entries"][-1]["type"] == "day":
        page["entries"].pop()
    page["heard_count"] = len(heard_entries)
    return page
