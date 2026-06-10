import os

import pytest

from dmr_teletext.db import LASTHEARD_QUERY, iter_lastheard_rows
from dmr_teletext.page_data import PAGE_ENTRY_LIMIT, build_page


def test_lastheard_query_fetches_raw_payload() -> None:
    assert "SELECT received_at, payload" in LASTHEARD_QUERY
    assert "payload->>'ContextID' LIKE '244___'" in LASTHEARD_QUERY
    assert "payload->>'SourceCall' <> ''" in LASTHEARD_QUERY


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is required for PostgreSQL integration tests",
)
def test_build_page_from_postgresql() -> None:
    page = build_page(iter_lastheard_rows(os.environ["DATABASE_URL"]))

    assert len(page["entries"]) <= PAGE_ENTRY_LIMIT
    assert page["row_count"] == len(page["entries"])
