import os

import pytest

from bm_teletext_collector.db import EventStore


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is required for PostgreSQL integration tests",
)
def test_schema_and_append_event_against_postgresql() -> None:
    store = EventStore(os.environ["DATABASE_URL"])
    store.ensure_schema()
    store.append_event({"SourceID": 244123, "SessionID": "integration-test"})
