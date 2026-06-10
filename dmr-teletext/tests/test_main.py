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
