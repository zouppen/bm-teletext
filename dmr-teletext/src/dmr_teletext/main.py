from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dmr_teletext.db import iter_lastheard_rows, resolve_page_time
from dmr_teletext.page_data import (
    DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
    PAGE_ENTRY_LIMIT,
    build_page,
)
from dmr_teletext.text_format import format_page_ep1


TELETEXT_PAGE_ENTRY_LIMIT = 16


@dataclass(frozen=True)
class CliOptions:
    output_format: str
    page_entry_limit: int
    page_time: str | None
    rssi_repair_window_seconds: int
    subpage: str | None
    rssi_yellow_threshold: int
    output_file: str | None


class CliArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        usage = self.format_usage().strip()
        raise ValueError(f"{usage}\n{self.prog}: error: {message}")


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer")
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def subpage_text(value: str) -> str:
    if len(value) != 5:
        raise argparse.ArgumentTypeError("must be exactly 5 characters")
    return value


def create_argument_parser() -> argparse.ArgumentParser:
    parser = CliArgumentParser(prog="dmr-teletext-page-data")
    parser.add_argument("--page-time")
    parser.add_argument(
        "--rssi-repair-window-seconds",
        type=non_negative_int,
        default=DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
    )
    subparsers = parser.add_subparsers(
        dest="output_format",
        required=True,
        parser_class=CliArgumentParser,
    )

    json_parser = subparsers.add_parser("json")
    json_parser.add_argument(
        "--page-entry-limit",
        type=positive_int,
        default=PAGE_ENTRY_LIMIT,
    )

    teletext_parser = subparsers.add_parser("teletext")
    teletext_parser.set_defaults(page_entry_limit=TELETEXT_PAGE_ENTRY_LIMIT)
    teletext_parser.add_argument("--subpage", type=subpage_text, required=True)
    teletext_parser.add_argument(
        "--rssi-yellow-threshold",
        type=int,
        default=-90,
    )
    teletext_parser.add_argument("output_file")

    return parser


def parse_cli_options(argv: list[str]) -> CliOptions:
    namespace = create_argument_parser().parse_args(argv)
    return CliOptions(
        output_format=namespace.output_format,
        page_entry_limit=namespace.page_entry_limit,
        page_time=namespace.page_time,
        rssi_repair_window_seconds=namespace.rssi_repair_window_seconds,
        subpage=getattr(namespace, "subpage", None),
        rssi_yellow_threshold=getattr(namespace, "rssi_yellow_threshold", -90),
        output_file=getattr(namespace, "output_file", None),
    )


def resolve_cli_page_time(database_url: str, value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)

    try:
        return resolve_page_time(database_url, value)
    except ValueError as exc:
        raise ValueError("--page-time must be a PostgreSQL timestamptz value") from exc


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
        page_time = resolve_cli_page_time(database_url, options.page_time)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    page = build_page(
        iter_lastheard_rows(database_url, page_time),
        repair_window_seconds=options.rssi_repair_window_seconds,
        page_time=page_time,
        page_entry_limit=options.page_entry_limit,
    )
    if options.output_format == "teletext":
        Path(options.output_file or "").write_bytes(
            format_page_ep1(
                page,
                subpage=options.subpage or "",
                rssi_yellow_threshold=options.rssi_yellow_threshold,
            )
        )
    else:
        print(json.dumps(page, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
