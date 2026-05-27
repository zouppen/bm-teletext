from __future__ import annotations

from collections.abc import Mapping
from typing import Any


MIN_FINNISH_REPEATER_ID = 244000
MAX_FINNISH_REPEATER_ID = 244999


def parse_source_id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        source_id = value
    elif isinstance(value, str):
        text = value.strip()
        if len(text) != 6 or not text.isdigit():
            return None
        source_id = int(text)
    else:
        return None

    if source_id < 100000 or source_id > 999999:
        return None

    return source_id


def is_finnish_repeater_event(payload: Mapping[str, Any]) -> bool:
    source_id = parse_source_id(payload.get("SourceID"))
    return (
        source_id is not None
        and MIN_FINNISH_REPEATER_ID <= source_id <= MAX_FINNISH_REPEATER_ID
    )
