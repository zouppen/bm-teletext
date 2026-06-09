from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lastheard_events (
    id bigserial PRIMARY KEY,
    received_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL
);

CREATE INDEX IF NOT EXISTS lastheard_events_received_at_idx
    ON lastheard_events (received_at);

DROP INDEX IF EXISTS lastheard_events_source_id_idx;

CREATE INDEX IF NOT EXISTS lastheard_events_context_id_idx
    ON lastheard_events ((payload->>'ContextID'));
"""


class EventStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def ensure_schema(self) -> None:
        import psycopg

        with psycopg.connect(self._database_url) as conn:
            conn.execute(SCHEMA_SQL)

    def append_event(self, payload: Mapping[str, Any]) -> None:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as conn:
            conn.execute(
                "INSERT INTO lastheard_events (payload) VALUES (%s)",
                (Jsonb(dict(payload)),),
            )
