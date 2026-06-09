from __future__ import annotations

import logging
import re
import sys

from bm_collector.config import load_config
from bm_collector.db import EventStore
from bm_collector.filters import ContextIdFilter
from bm_collector.stream import LastHeardCollector


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    try:
        config = load_config()
        context_id_filter = ContextIdFilter(config.context_id_pattern)
    except (RuntimeError, re.error) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    configure_logging(config.log_level)

    store = EventStore(config.database_url)
    store.ensure_schema()

    collector = LastHeardCollector(
        store=store,
        url=config.lastheard_url,
        socketio_path=config.socketio_path,
        context_id_filter=context_id_filter,
    )
    collector.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
