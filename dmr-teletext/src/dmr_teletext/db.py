from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from dmr_teletext.page_data import LastHeardRow


LASTHEARD_QUERY = """
SELECT received_at, payload
FROM lastheard_events
WHERE payload->>'ContextID' LIKE '244___'
  AND payload->>'SourceCall' <> ''
  AND received_at < %(page_time)s
ORDER BY received_at DESC
"""


def resolve_page_time(database_url: str, value: str) -> datetime:
    import psycopg

    try:
        with psycopg.connect(database_url) as conn:
            row = conn.execute("SELECT %s::timestamptz", (value,)).fetchone()
    except psycopg.Error as exc:
        raise ValueError("invalid PostgreSQL timestamptz value") from exc

    if row is None:
        raise ValueError("invalid PostgreSQL timestamptz value")
    return row[0]


def iter_lastheard_rows(database_url: str, page_time: datetime) -> Iterator[LastHeardRow]:
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor(name="dmr_teletext_lastheard") as cur:
            cur.execute(LASTHEARD_QUERY, {"page_time": page_time})
            for received_at, payload in cur:
                yield LastHeardRow(received_at=received_at, payload=payload)
