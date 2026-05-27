from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import logging
import time
from typing import Any, Protocol

from bm_teletext_collector.filters import is_finnish_repeater_event


LOGGER = logging.getLogger(__name__)


class Store(Protocol):
    def append_event(self, payload: Mapping[str, Any]) -> None:
        ...


@dataclass
class LastHeardCollector:
    store: Store
    url: str
    socketio_path: str
    reconnect_delay_seconds: float = 5.0
    insert_retry_delay_seconds: float = 5.0

    def run_forever(self) -> None:
        import socketio

        while True:
            client = socketio.Client(reconnection=True)

            @client.event
            def connect() -> None:
                LOGGER.info("connected to BrandMeister Last Heard")

            @client.event
            def disconnect() -> None:
                LOGGER.warning("disconnected from BrandMeister Last Heard")

            @client.on("mqtt")
            def on_mqtt(data: Mapping[str, Any]) -> None:
                self.handle_mqtt(data)

            try:
                client.connect(
                    url=self.url,
                    socketio_path=self.socketio_path,
                    transports=["websocket"],
                )
                client.wait()
            except KeyboardInterrupt:
                LOGGER.info("collector stopped")
                client.disconnect()
                raise
            except Exception:
                LOGGER.exception(
                    "Last Heard stream failed; retrying in %.1f seconds",
                    self.reconnect_delay_seconds,
                )
                try:
                    client.disconnect()
                except Exception:
                    LOGGER.debug("disconnect after failure also failed", exc_info=True)
                time.sleep(self.reconnect_delay_seconds)

    def handle_mqtt(self, data: Mapping[str, Any]) -> bool:
        payload = decode_mqtt_payload(data)
        if payload is None:
            return False

        if not is_finnish_repeater_event(payload):
            return False

        self.append_with_retry(payload)
        LOGGER.info("stored event SourceID=%s", payload.get("SourceID"))
        return True

    def append_with_retry(self, payload: Mapping[str, Any]) -> None:
        while True:
            try:
                self.store.append_event(payload)
                return
            except Exception:
                LOGGER.exception(
                    "database insert failed; retrying in %.1f seconds",
                    self.insert_retry_delay_seconds,
                )
                time.sleep(self.insert_retry_delay_seconds)


def decode_mqtt_payload(data: Mapping[str, Any]) -> dict[str, Any] | None:
    raw_payload = data.get("payload")
    if isinstance(raw_payload, str):
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            LOGGER.warning("skipping invalid JSON payload")
            return None
    elif isinstance(raw_payload, dict):
        payload = raw_payload
    else:
        LOGGER.debug("skipping mqtt message without object payload")
        return None

    if not isinstance(payload, dict):
        LOGGER.debug("skipping non-object payload")
        return None

    return payload
