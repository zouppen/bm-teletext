from __future__ import annotations

from dataclasses import dataclass
import os

from bm_collector.filters import DEFAULT_CONTEXT_ID_PATTERN


DEFAULT_LASTHEARD_URL = "https://api.brandmeister.network"
DEFAULT_SOCKETIO_PATH = "/lh"
DEFAULT_LOG_LEVEL = "INFO"


@dataclass(frozen=True)
class Config:
    database_url: str
    lastheard_url: str = DEFAULT_LASTHEARD_URL
    socketio_path: str = DEFAULT_SOCKETIO_PATH
    context_id_pattern: str = DEFAULT_CONTEXT_ID_PATTERN
    log_level: str = DEFAULT_LOG_LEVEL


def load_config() -> Config:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    return Config(
        database_url=database_url,
        lastheard_url=os.environ.get("BM_LASTHEARD_URL", DEFAULT_LASTHEARD_URL),
        socketio_path=os.environ.get(
            "BM_LASTHEARD_SOCKETIO_PATH",
            DEFAULT_SOCKETIO_PATH,
        ),
        context_id_pattern=os.environ.get(
            "BM_CONTEXT_ID_PATTERN",
            DEFAULT_CONTEXT_ID_PATTERN,
        ),
        log_level=os.environ.get("BM_LOG_LEVEL", DEFAULT_LOG_LEVEL),
    )
