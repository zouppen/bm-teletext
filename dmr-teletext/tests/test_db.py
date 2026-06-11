import os
from datetime import datetime, timezone

import pytest

from dmr_teletext.db import LASTHEARD_QUERY, iter_lastheard_rows, resolve_page_time
from dmr_teletext.page_data import PAGE_ENTRY_LIMIT, build_page


def test_lastheard_query_fetches_raw_payload() -> None:
    assert "SELECT received_at, payload" in LASTHEARD_QUERY
    assert "payload->>'ContextID' LIKE '244___'" in LASTHEARD_QUERY
    assert "payload->>'SourceCall' <> ''" in LASTHEARD_QUERY
    assert "received_at < %(page_time)s" in LASTHEARD_QUERY


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is required for PostgreSQL integration tests",
)
def test_build_page_from_postgresql() -> None:
    page_time = datetime.now(timezone.utc)
    page = build_page(
        iter_lastheard_rows(os.environ["DATABASE_URL"], page_time),
        page_time=page_time,
    )
    heard_entries = [
        entry for entry in page["entries"] if entry["type"] == "heard"
    ]

    assert len(heard_entries) <= PAGE_ENTRY_LIMIT
    assert page["heard_count"] == len(heard_entries)


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is required for PostgreSQL integration tests",
)
def test_resolve_page_time_from_postgresql() -> None:
    page_time = resolve_page_time(
        os.environ["DATABASE_URL"],
        "2026-06-10 12:00:00+00",
    )

    assert page_time == datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
