import logging
from typing import Any

from bm_collector.main import configure_logging


def test_configure_logging_omits_application_timestamp(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_basic_config(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    configure_logging("INFO")

    assert captured["level"] == logging.INFO
    assert captured["format"] == "%(levelname)s %(name)s: %(message)s"
    assert "asctime" not in captured["format"]
