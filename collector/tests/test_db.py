import os

import pytest
import psycopg

from bm_teletext_collector.db import EventStore


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is required for PostgreSQL integration tests",
)
def test_schema_and_append_event_against_postgresql() -> None:
    database_url = os.environ["DATABASE_URL"]
    store = EventStore(database_url)
    store.ensure_schema()
    store.append_event(
        {"ContextID": 244123, "SourceID": 9999999, "SessionID": "integration-test"}
    )

    with psycopg.connect(database_url) as conn:
        indexes = {
            row[0]
            for row in conn.execute(
                """
                select indexname
                from pg_indexes
                where schemaname = 'public' and tablename = 'lastheard_events'
                """
            )
        }

    assert "lastheard_events_context_id_idx" in indexes
    assert "lastheard_events_source_id_idx" not in indexes
