from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

from dmr_teletext.db import iter_lastheard_rows, resolve_page_time
from dmr_teletext.page_data import DEFAULT_RSSI_REPAIR_WINDOW_SECONDS, build_page
from dmr_teletext.text_format import format_page_text


RSSI_REPAIR_WINDOW_ENV = "DMR_TELETEXT_RSSI_REPAIR_WINDOW_SECONDS"
PAGE_TIME_ENV = "DMR_TELETEXT_PAGE_TIME"
OUTPUT_FORMATS = {"json", "text"}


def get_rssi_repair_window_seconds() -> int:
    value = os.environ.get(RSSI_REPAIR_WINDOW_ENV)
    if value is None:
        return DEFAULT_RSSI_REPAIR_WINDOW_SECONDS

    try:
        seconds = int(value)
    except ValueError:
        raise ValueError(f"{RSSI_REPAIR_WINDOW_ENV} must be a non-negative integer")

    if seconds < 0:
        raise ValueError(f"{RSSI_REPAIR_WINDOW_ENV} must be a non-negative integer")
    return seconds


def get_page_time(database_url: str) -> datetime:
    value = os.environ.get(PAGE_TIME_ENV)
    if value is None:
        return datetime.now(timezone.utc)

    try:
        return resolve_page_time(database_url, value)
    except ValueError as exc:
        raise ValueError(f"{PAGE_TIME_ENV} must be a PostgreSQL timestamptz value") from exc


def get_output_format(argv: list[str]) -> str:
    if not argv:
        return "json"
    if len(argv) == 1 and argv[0] in OUTPUT_FORMATS:
        return argv[0]
    raise ValueError("usage: dmr-teletext-page-data [json|text]")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        output_format = get_output_format(argv)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    try:
        repair_window_seconds = get_rssi_repair_window_seconds()
        page_time = get_page_time(database_url)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    page = build_page(
        iter_lastheard_rows(database_url, page_time),
        repair_window_seconds=repair_window_seconds,
        page_time=page_time,
    )
    if output_format == "text":
        print(format_page_text(page))
    else:
        print(json.dumps(page, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
