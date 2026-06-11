from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dmr_teletext.page_data import PageData, PageEntry


LINE_WIDTH = 40
TIME_WIDTH = 5
CALLSIGN_WIDTH = 8
REPEATER_WIDTH = 18
RSSI_WIDTH = 4
BE_WIDTH = 1


def format_page_text(page: PageData) -> str:
    return "\n".join([format_header(), *format_entries(page["entries"])])


def format_entries(entries: list[PageEntry]) -> list[str]:
    return [format_entry(entry) for entry in entries]


def format_header() -> str:
    return format_columns("AIKA", "KUTSU", "TOISTIN", "RSSI", "B")


def format_entry(entry: PageEntry) -> str:
    if entry["type"] == "day":
        return format_day(entry["time"])
    return format_heard(entry)


def format_day(value: str) -> str:
    day = parse_local_time(value).date().isoformat()
    return day[:LINE_WIDTH]


def format_heard(entry: PageEntry) -> str:
    time_text = parse_local_time(entry["time"]).strftime("%H:%M")
    rssi = format_rssi(entry["rssi"])
    marker = "*" if entry["be"] else ""
    return format_columns(
        time_text,
        entry["callsign"] or "",
        entry["repeater"] or "",
        rssi,
        marker,
    )


def format_columns(
    time_text: str,
    callsign: str,
    repeater: str,
    rssi: str,
    be: str,
) -> str:
    line = (
        f"{truncate(time_text, TIME_WIDTH):<{TIME_WIDTH}} "
        f"{truncate(callsign, CALLSIGN_WIDTH):<{CALLSIGN_WIDTH}} "
        f"{truncate(repeater, REPEATER_WIDTH):<{REPEATER_WIDTH}} "
        f"{truncate(rssi, RSSI_WIDTH):>{RSSI_WIDTH}} "
        f"{truncate(be, BE_WIDTH):<{BE_WIDTH}}"
    )
    return line[:LINE_WIDTH]


def format_rssi(value: Any) -> str:
    try:
        rssi = float(value)
    except (TypeError, ValueError):
        return ""
    if rssi >= 0:
        return ""
    return str(round(rssi))


def parse_local_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


def truncate(value: str, width: int) -> str:
    return value[:width]
