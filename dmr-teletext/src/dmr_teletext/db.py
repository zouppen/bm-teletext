from __future__ import annotations

from collections.abc import Iterator

from dmr_teletext.page_data import LastHeardRow


LASTHEARD_QUERY = """
SELECT received_at, payload
FROM lastheard_events
WHERE payload->>'ContextID' LIKE '244___'
  AND payload->>'SourceCall' <> ''
ORDER BY received_at DESC
"""


def iter_lastheard_rows(database_url: str) -> Iterator[LastHeardRow]:
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor(name="dmr_teletext_lastheard") as cur:
            cur.execute(LASTHEARD_QUERY)
            for received_at, payload in cur:
                yield LastHeardRow(received_at=received_at, payload=payload)
