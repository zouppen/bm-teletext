from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import re
from typing import Any, Pattern


DEFAULT_SOURCE_ID_PATTERN = r"^244...$"


def source_id_to_string(value: Any) -> str | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if not value.is_integer():
            return None
        return str(int(value))

    if isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            return None
        return str(int(text))

    return None


@dataclass(frozen=True)
class SourceIdFilter:
    pattern: str = DEFAULT_SOURCE_ID_PATTERN
    _compiled_pattern: Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_compiled_pattern", re.compile(self.pattern))

    def matches_payload(self, payload: Mapping[str, Any]) -> bool:
        source_id = source_id_to_string(payload.get("SourceID"))
        return (
            source_id is not None
            and self._compiled_pattern.fullmatch(source_id) is not None
        )


DEFAULT_SOURCE_ID_FILTER = SourceIdFilter()


def parse_source_id(value: Any) -> int | None:
    source_id = source_id_to_string(value)
    if source_id is None:
        return None

    return int(source_id)


def is_finnish_repeater_event(payload: Mapping[str, Any]) -> bool:
    return DEFAULT_SOURCE_ID_FILTER.matches_payload(payload)
