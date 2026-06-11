from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from dmr_teletext.page_data import (
    HeardEntry,
    PageData,
    PageEntry,
    has_bit_errors,
    payload_text,
)


LINE_WIDTH = 40
TIME_WIDTH = 5
CALLSIGN_WIDTH = 8
TEXT_REPEATER_WIDTH = 18
EP1_REPEATER_WIDTH = 16
RSSI_WIDTH = 4
BE_WIDTH = 1
EP1_PREFIX = b"\xfe\x01\x18\x00\x00\x00"
EP1_SUFFIX = b"\x00\x00"
EP1_PAGE_ROWS = 25
EP1_TEMPLATE_ROWS = 6
EP1_FOOTER_ROWS = 3
EP1_ENTRY_ROWS = EP1_PAGE_ROWS - EP1_TEMPLATE_ROWS - EP1_FOOTER_ROWS


def format_page_text(page: PageData) -> str:
    return "\n".join([format_header(), *format_entries(page["entries"])])


def format_page_ep1(
    page: PageData,
    subpage: str,
    rssi_yellow_threshold: int = -90,
) -> bytes:
    page_time = parse_local_time(page["page_time"])
    rows = [
        b" " * LINE_WIDTH,
        ep1_row(
            b" \x1d\x01\rDemarit\x0c \x02\x1c P{ivitetty "
            + page_time.strftime("%H:%M").encode("ascii")
            + b"  \x07"
            + encode_teletext(subpage, 5, align="<")
        ),
        ep1_row(b" \x1d            \x1c                         "),
        ep1_row(b"\x01\x1d\x07 FinDMR:n viimeksi kuullut asemat"),
        b" " * LINE_WIDTH,
        ep1_row(b"\x03Aika  Kutsu    Toistin          RSSI * "),
    ]
    entries = page["entries"][:EP1_ENTRY_ROWS]
    rows.extend(format_ep1_entry(entry, rssi_yellow_threshold) for entry in entries)
    rows.extend([b" " * LINE_WIDTH] * (EP1_ENTRY_ROWS - len(entries)))
    rows.extend(
        [
            ep1_row(b"\x03Suomen aikaa. *) Bittivirheit{"),
            ep1_row(b"\x03Katso lis{{: brandmeister.network"),
            b" " * LINE_WIDTH,
        ]
    )
    return EP1_PREFIX + b"".join(rows) + EP1_SUFFIX


def format_entries(entries: list[PageEntry]) -> list[str]:
    return [format_entry(entry) for entry in entries]


def format_header() -> str:
    return format_columns("AIKA", "KUTSU", "TOISTIN", "RSSI", "B")


def format_entry(entry: PageEntry) -> str:
    if entry["type"] == "day":
        return format_day(entry["time"])
    return format_heard(entry)


def format_day(value: str) -> str:
    day = (parse_local_time(value) - timedelta(days=1)).date().isoformat()
    return day[:LINE_WIDTH]


def format_heard(entry: PageEntry) -> str:
    time_text = parse_local_time(entry["time"]).strftime("%H:%M")
    payload = entry["payload"]
    rssi = format_rssi(payload.get("RSSI"))
    marker = "*" if has_bit_errors(payload.get("BER")) else ""
    return format_columns(
        time_text,
        heard_callsign(entry) or "",
        heard_repeater(entry) or "",
        rssi,
        marker,
    )


def heard_callsign(entry: HeardEntry) -> str | None:
    return payload_text(entry["payload"], "SourceCall")


def heard_repeater(entry: HeardEntry) -> str | None:
    return payload_text(entry["payload"], "LinkCall")


def format_columns(
    time_text: str,
    callsign: str,
    repeater: str,
    rssi: str,
    be: str,
) -> str:
    callsign = truncate_with_marker(callsign, CALLSIGN_WIDTH)
    line = (
        f"{truncate(time_text, TIME_WIDTH):<{TIME_WIDTH}} "
        f"{callsign:<{CALLSIGN_WIDTH}} "
        f"{truncate(repeater, TEXT_REPEATER_WIDTH):<{TEXT_REPEATER_WIDTH}} "
        f"{truncate(rssi, RSSI_WIDTH):>{RSSI_WIDTH}} "
        f"{truncate(be, BE_WIDTH):<{BE_WIDTH}}"
    )
    return line[:LINE_WIDTH]


def format_ep1_entry(entry: PageEntry, rssi_yellow_threshold: int) -> bytes:
    if entry["type"] == "day":
        return format_ep1_day(entry["time"])
    return format_ep1_heard(entry, rssi_yellow_threshold)


def format_ep1_day(value: str) -> bytes:
    day = (parse_local_time(value) - timedelta(days=1)).strftime("%d.%m.%Y")
    return ep1_row(
        b"\x05"
        + day.encode("ascii")
        + b"    \x17$$$ $,$$ $,$ $,$$$"
    )


def format_ep1_heard(entry: HeardEntry, rssi_yellow_threshold: int) -> bytes:
    time_text = parse_local_time(entry["time"]).strftime("%H:%M").encode("ascii")
    payload = entry["payload"]
    rssi = format_rssi(payload.get("RSSI"))
    rssi_field = format_ep1_rssi(payload.get("RSSI"), rssi, rssi_yellow_threshold)
    marker = b"B" if has_bit_errors(payload.get("BER")) else b" "
    return ep1_row(
        b" "
        + time_text
        + b"\x06"
        + encode_teletext(
            truncate_with_marker(heard_callsign(entry) or "", CALLSIGN_WIDTH),
            CALLSIGN_WIDTH,
            align="<",
        )
        + b"\x07"
        + encode_teletext(heard_repeater(entry) or "", EP1_REPEATER_WIDTH, align="<")
        + rssi_field
        + b"\x01"
        + marker
        + b" "
    )


def format_ep1_rssi(
    raw_value: Any,
    rssi_text: str,
    rssi_yellow_threshold: int,
) -> bytes:
    if not rssi_text:
        return b" " * 5
    try:
        rssi = float(raw_value)
    except (TypeError, ValueError):
        return b" " * 5
    colour = b"\x03" if rssi <= rssi_yellow_threshold else b"\x02"
    return colour + rssi_text.rjust(RSSI_WIDTH).encode("ascii")


def ep1_row(value: bytes) -> bytes:
    return value[:LINE_WIDTH].ljust(LINE_WIDTH, b" ")


def encode_teletext(value: str, width: int, align: str = "<") -> bytes:
    translated = value.translate(
        str.maketrans(
            {
                "Ä": "[",
                "Ö": "\\",
                "Å": "]",
                "ä": "{",
                "ö": "|",
                "å": "}",
            }
        )
    ).encode("ascii", errors="replace")
    translated = translated[:width]
    return f"{translated.decode('ascii'):{align}{width}}".encode("ascii")


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


def truncate_with_marker(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    return value[: width - 1] + ">"
