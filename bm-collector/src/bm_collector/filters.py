from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import re
from typing import Any, Pattern


DEFAULT_CONTEXT_ID_PATTERN = r"^244"


def context_id_to_string(value: Any) -> str | None:
    if value is None:
        return None

    return str(value)


@dataclass(frozen=True)
class ContextIdFilter:
    pattern: str = DEFAULT_CONTEXT_ID_PATTERN
    _compiled_pattern: Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_compiled_pattern", re.compile(self.pattern))

    def matches_payload(self, payload: Mapping[str, Any]) -> bool:
        context_id = context_id_to_string(payload.get("ContextID"))
        return (
            context_id is not None
            and self._compiled_pattern.search(context_id) is not None
        )


DEFAULT_CONTEXT_ID_FILTER = ContextIdFilter()


def is_finnish_repeater_event(payload: Mapping[str, Any]) -> bool:
    return DEFAULT_CONTEXT_ID_FILTER.matches_payload(payload)
