from __future__ import annotations

import json
import os
import sys

from dmr_teletext.db import iter_lastheard_rows
from dmr_teletext.page_data import DEFAULT_RSSI_REPAIR_WINDOW_SECONDS, build_page


RSSI_REPAIR_WINDOW_ENV = "DMR_TELETEXT_RSSI_REPAIR_WINDOW_SECONDS"


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


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    try:
        repair_window_seconds = get_rssi_repair_window_seconds()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    page = build_page(
        iter_lastheard_rows(database_url),
        repair_window_seconds=repair_window_seconds,
    )
    print(json.dumps(page, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
