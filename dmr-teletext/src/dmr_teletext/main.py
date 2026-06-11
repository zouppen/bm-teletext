from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from dmr_teletext.db import iter_lastheard_rows, resolve_page_time
from dmr_teletext.page_data import (
    DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
    PAGE_ENTRY_LIMIT,
    build_page,
)
from dmr_teletext.text_format import format_page_text


RSSI_REPAIR_WINDOW_ENV = "DMR_TELETEXT_RSSI_REPAIR_WINDOW_SECONDS"
PAGE_TIME_ENV = "DMR_TELETEXT_PAGE_TIME"


@dataclass(frozen=True)
class CliOptions:
    output_format: str
    page_entry_limit: int


class CliArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        usage = self.format_usage().strip()
        raise ValueError(f"{usage}\n{self.prog}: error: {message}")


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


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer")
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def create_argument_parser() -> argparse.ArgumentParser:
    parser = CliArgumentParser(prog="dmr-teletext-page-data")
    subparsers = parser.add_subparsers(dest="output_format", required=True)

    json_parser = subparsers.add_parser("json")
    json_parser.add_argument(
        "--page-entry-limit",
        type=positive_int,
        default=PAGE_ENTRY_LIMIT,
    )

    text_parser = subparsers.add_parser("text")
    text_parser.set_defaults(page_entry_limit=PAGE_ENTRY_LIMIT)

    return parser


def parse_cli_options(argv: list[str]) -> CliOptions:
    namespace = create_argument_parser().parse_args(argv)
    return CliOptions(
        output_format=namespace.output_format,
        page_entry_limit=namespace.page_entry_limit,
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        options = parse_cli_options(argv)
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
        page_entry_limit=(
            options.page_entry_limit
            if options.output_format == "json"
            else PAGE_ENTRY_LIMIT
        ),
    )
    if options.output_format == "text":
        print(format_page_text(page))
    else:
        print(json.dumps(page, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
