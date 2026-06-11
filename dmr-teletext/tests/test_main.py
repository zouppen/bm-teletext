import json
from datetime import datetime, timezone

import pytest

from dmr_teletext import main as main_module
from dmr_teletext.page_data import DEFAULT_RSSI_REPAIR_WINDOW_SECONDS


def test_get_rssi_repair_window_seconds_uses_default(monkeypatch) -> None:
    monkeypatch.delenv(main_module.RSSI_REPAIR_WINDOW_ENV, raising=False)

    assert (
        main_module.get_rssi_repair_window_seconds()
        == DEFAULT_RSSI_REPAIR_WINDOW_SECONDS
    )


def test_get_rssi_repair_window_seconds_uses_env_value(monkeypatch) -> None:
    monkeypatch.setenv(main_module.RSSI_REPAIR_WINDOW_ENV, "42")

    assert main_module.get_rssi_repair_window_seconds() == 42


@pytest.mark.parametrize("value", ["bad", "-1"])
def test_get_rssi_repair_window_seconds_rejects_invalid_values(
    monkeypatch, value: str
) -> None:
    monkeypatch.setenv(main_module.RSSI_REPAIR_WINDOW_ENV, value)

    with pytest.raises(ValueError, match="must be a non-negative integer"):
        main_module.get_rssi_repair_window_seconds()


def test_main_rejects_invalid_rssi_repair_window(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/unused")
    monkeypatch.setenv(main_module.RSSI_REPAIR_WINDOW_ENV, "bad")

    assert main_module.main() == 2

    captured = capsys.readouterr()
    assert "must be a non-negative integer" in captured.err


def test_get_page_time_uses_current_time_by_default(monkeypatch) -> None:
    monkeypatch.delenv(main_module.PAGE_TIME_ENV, raising=False)

    before = datetime.now(timezone.utc)
    page_time = main_module.get_page_time("postgresql://example/unused")
    after = datetime.now(timezone.utc)

    assert before <= page_time <= after


def test_get_page_time_resolves_env_value_with_postgresql(monkeypatch) -> None:
    resolved = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    calls = []

    def fake_resolve_page_time(database_url: str, value: str) -> datetime:
        calls.append((database_url, value))
        return resolved

    monkeypatch.setenv(main_module.PAGE_TIME_ENV, "2026-06-10 12:00:00+00")
    monkeypatch.setattr(main_module, "resolve_page_time", fake_resolve_page_time)

    assert main_module.get_page_time("postgresql://example/unused") == resolved
    assert calls == [
        ("postgresql://example/unused", "2026-06-10 12:00:00+00")
    ]


def test_get_page_time_rejects_invalid_env_value(monkeypatch) -> None:
    def fake_resolve_page_time(database_url: str, value: str) -> datetime:
        raise ValueError("invalid PostgreSQL timestamptz value")

    monkeypatch.setenv(main_module.PAGE_TIME_ENV, "bad")
    monkeypatch.setattr(main_module, "resolve_page_time", fake_resolve_page_time)

    with pytest.raises(ValueError, match="must be a PostgreSQL timestamptz value"):
        main_module.get_page_time("postgresql://example/unused")


def test_main_passes_page_time_to_query_and_output(monkeypatch, capsys) -> None:
    page_time = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    calls = []

    def fake_iter_lastheard_rows(database_url, effective_page_time):
        calls.append(("iter", database_url, effective_page_time))
        return iter(())

    def fake_build_page(rows, repair_window_seconds, page_time):
        calls.append(("build", list(rows), repair_window_seconds, page_time))
        return {
            "page_time": page_time.isoformat(),
            "page_entry_limit": 20,
            "heard_count": 0,
            "entries": [],
        }

    monkeypatch.setenv("DATABASE_URL", "postgresql://example/unused")
    monkeypatch.setattr(main_module, "get_page_time", lambda database_url: page_time)
    monkeypatch.setattr(main_module, "iter_lastheard_rows", fake_iter_lastheard_rows)
    monkeypatch.setattr(main_module, "build_page", fake_build_page)

    assert main_module.main() == 0

    assert calls == [
        ("iter", "postgresql://example/unused", page_time),
        ("build", [], DEFAULT_RSSI_REPAIR_WINDOW_SECONDS, page_time),
    ]
    assert json.loads(capsys.readouterr().out)["page_time"] == page_time.isoformat()


def test_main_rejects_invalid_page_time(monkeypatch, capsys) -> None:
    def fake_get_page_time(database_url: str) -> datetime:
        raise ValueError(
            f"{main_module.PAGE_TIME_ENV} must be a PostgreSQL timestamptz value"
        )

    monkeypatch.setenv("DATABASE_URL", "postgresql://example/unused")
    monkeypatch.setattr(main_module, "get_page_time", fake_get_page_time)

    assert main_module.main() == 2

    captured = capsys.readouterr()
    assert main_module.PAGE_TIME_ENV in captured.err
