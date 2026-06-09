from typing import Any

from bm_teletext_collector.filters import SourceIdFilter
from bm_teletext_collector.stream import LastHeardCollector, decode_mqtt_payload


class FakeStore:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def append_event(self, payload: dict[str, Any]) -> None:
        self.payloads.append(payload)


def test_decodes_socketio_mqtt_payload_json_string() -> None:
    assert decode_mqtt_payload({"payload": '{"SourceID": 244123}'}) == {
        "SourceID": 244123
    }


def test_rejects_invalid_mqtt_payload() -> None:
    assert decode_mqtt_payload({"payload": "not-json"}) is None
    assert decode_mqtt_payload({"payload": '["not", "object"]'}) is None
    assert decode_mqtt_payload({}) is None


def test_appends_all_matching_events_without_deduplication() -> None:
    store = FakeStore()
    collector = LastHeardCollector(
        store=store,
        url="https://example.invalid",
        socketio_path="/lh",
        source_id_filter=SourceIdFilter(),
    )
    message = {"payload": '{"SourceID": 244123, "SessionID": "abc"}'}

    assert collector.handle_mqtt(message)
    assert collector.handle_mqtt(message)

    assert store.payloads == [
        {"SourceID": 244123, "SessionID": "abc"},
        {"SourceID": 244123, "SessionID": "abc"},
    ]


def test_skips_non_matching_events() -> None:
    store = FakeStore()
    collector = LastHeardCollector(
        store=store,
        url="https://example.invalid",
        socketio_path="/lh",
        source_id_filter=SourceIdFilter(),
    )

    assert not collector.handle_mqtt({"payload": '{"SourceID": 2441234}'})
    assert store.payloads == []


def test_collector_uses_configured_source_id_filter() -> None:
    store = FakeStore()
    collector = LastHeardCollector(
        store=store,
        url="https://example.invalid",
        socketio_path="/lh",
        source_id_filter=SourceIdFilter(r"^999.*$"),
    )

    assert collector.handle_mqtt({"payload": '{"SourceID": 999123}'})
    assert not collector.handle_mqtt({"payload": '{"SourceID": 244123}'})
    assert store.payloads == [{"SourceID": 999123}]
