from __future__ import annotations

import logging
import sys

from bm_teletext_collector.config import load_config
from bm_teletext_collector.db import EventStore
from bm_teletext_collector.stream import LastHeardCollector


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    try:
        config = load_config()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    configure_logging(config.log_level)

    store = EventStore(config.database_url)
    store.ensure_schema()

    collector = LastHeardCollector(
        store=store,
        url=config.lastheard_url,
        socketio_path=config.socketio_path,
    )
    collector.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
