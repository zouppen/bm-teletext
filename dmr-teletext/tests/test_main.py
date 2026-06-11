import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from dmr_teletext import main as main_module
from dmr_teletext.page_data import (
    DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
    PAGE_ENTRY_LIMIT,
    LastHeardRow,
)


@pytest.fixture
def set_timezone(monkeypatch):
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset is required to test local timezone behavior")

    original_tz = os.environ.get("TZ")

    def apply(value: str) -> None:
        monkeypatch.setenv("TZ", value)
        time.tzset()

    yield apply

    if original_tz is None:
        monkeypatch.delenv("TZ", raising=False)
    else:
        monkeypatch.setenv("TZ", original_tz)
    time.tzset()


def test_parse_cli_options_rejects_missing_subcommand() -> None:
    with pytest.raises(ValueError, match="usage:"):
        main_module.parse_cli_options([])


def test_parse_cli_options_accepts_known_subcommands() -> None:
    assert main_module.parse_cli_options(["json"]) == main_module.CliOptions(
        output_format="json",
        page_entry_limit=PAGE_ENTRY_LIMIT,
        page_time=None,
        rssi_repair_window_seconds=DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
        subpage=None,
        rssi_yellow_threshold=-90,
    )
    assert main_module.parse_cli_options(
        ["teletext", "--subpage", "11/12"]
    ) == main_module.CliOptions(
        output_format="teletext",
        page_entry_limit=main_module.TELETEXT_PAGE_ENTRY_LIMIT,
        page_time=None,
        rssi_repair_window_seconds=DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
        subpage="11/12",
        rssi_yellow_threshold=-90,
    )


def test_parse_cli_options_accepts_json_page_entry_limit() -> None:
    assert main_module.parse_cli_options(
        ["json", "--page-entry-limit", "3"]
    ) == main_module.CliOptions(
        output_format="json",
        page_entry_limit=3,
        page_time=None,
        rssi_repair_window_seconds=DEFAULT_RSSI_REPAIR_WINDOW_SECONDS,
        subpage=None,
        rssi_yellow_threshold=-90,
    )


def test_parse_cli_options_accepts_global_options() -> None:
    assert main_module.parse_cli_options(
        [
            "--page-time",
            "2026-06-10 12:00:00+00",
            "--rssi-repair-window-seconds",
            "0",
            "teletext",
            "--subpage",
            "11/12",
            "--rssi-yellow-threshold",
            "-95",
        ]
    ) == main_module.CliOptions(
        output_format="teletext",
        page_entry_limit=main_module.TELETEXT_PAGE_ENTRY_LIMIT,
        page_time="2026-06-10 12:00:00+00",
        rssi_repair_window_seconds=0,
        subpage="11/12",
        rssi_yellow_threshold=-95,
    )


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["bad"],
        ["json", "extra"],
        ["json", "--page-entry-limit", "bad"],
        ["json", "--page-entry-limit", "0"],
        ["json", "--page-entry-limit", "-1"],
        ["text", "--page-entry-limit", "3"],
        ["teletext", "--page-entry-limit", "3"],
        ["teletext"],
        ["teletext", "--subpage", "1234"],
        ["teletext", "--subpage", "123456"],
        ["--rssi-repair-window-seconds", "bad", "json"],
        ["--rssi-repair-window-seconds", "-1", "json"],
        ["json", "--rssi-repair-window-seconds", "42"],
        ["json", "--subpage", "11/12"],
        ["json", "--rssi-yellow-threshold", "-95"],
        ["text"],
    ],
)
def test_parse_cli_options_rejects_invalid_arguments(argv) -> None:
    with pytest.raises(ValueError, match="usage:"):
        main_module.parse_cli_options(argv)


def test_resolve_cli_page_time_uses_current_time_by_default() -> None:
    before = datetime.now(timezone.utc)
    page_time = main_module.resolve_cli_page_time(
        "postgresql://example/unused",
        None,
    )
    after = datetime.now(timezone.utc)

    assert before <= page_time <= after


def test_resolve_cli_page_time_resolves_value_with_postgresql(monkeypatch) -> None:
    resolved = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    calls = []

    def fake_resolve_page_time(database_url: str, value: str) -> datetime:
        calls.append((database_url, value))
        return resolved

    monkeypatch.setattr(main_module, "resolve_page_time", fake_resolve_page_time)

    assert main_module.resolve_cli_page_time(
        "postgresql://example/unused",
        "2026-06-10 12:00:00+00",
    ) == resolved
    assert calls == [
        ("postgresql://example/unused", "2026-06-10 12:00:00+00")
    ]


def test_resolve_cli_page_time_rejects_invalid_value(monkeypatch) -> None:
    def fake_resolve_page_time(database_url: str, value: str) -> datetime:
        raise ValueError("invalid PostgreSQL timestamptz value")

    monkeypatch.setattr(main_module, "resolve_page_time", fake_resolve_page_time)

    with pytest.raises(
        ValueError,
        match="--page-time must be a PostgreSQL timestamptz value",
    ):
        main_module.resolve_cli_page_time("postgresql://example/unused", "bad")


def test_main_passes_page_time_to_query_and_output(monkeypatch, capsys) -> None:
    page_time = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    calls = []

    def fake_resolve_page_time(database_url, value):
        calls.append(("resolve", database_url, value))
        return page_time

    def fake_iter_lastheard_rows(database_url, effective_page_time):
        calls.append(("iter", database_url, effective_page_time))
        return iter(())

    def fake_build_page(rows, repair_window_seconds, page_time, page_entry_limit):
        calls.append(
            ("build", list(rows), repair_window_seconds, page_time, page_entry_limit)
        )
        return {
            "page_time": page_time.isoformat(),
            "page_entry_limit": page_entry_limit,
            "retained_callsign_count": 0,
            "rows_iterated": 0,
            "entries": [],
        }

    monkeypatch.setenv("DATABASE_URL", "postgresql://example/unused")
    monkeypatch.setattr(main_module, "resolve_page_time", fake_resolve_page_time)
    monkeypatch.setattr(main_module, "iter_lastheard_rows", fake_iter_lastheard_rows)
    monkeypatch.setattr(main_module, "build_page", fake_build_page)

    assert main_module.main(
        [
            "--page-time",
            "2026-06-10 12:00:00+00",
            "--rssi-repair-window-seconds",
            "42",
            "json",
        ]
    ) == 0

    assert calls == [
        (
            "resolve",
            "postgresql://example/unused",
            "2026-06-10 12:00:00+00",
        ),
        ("iter", "postgresql://example/unused", page_time),
        (
            "build",
            [],
            42,
            page_time,
            PAGE_ENTRY_LIMIT,
        ),
    ]
    assert json.loads(capsys.readouterr().out)["page_time"] == page_time.isoformat()


def test_main_rejects_invalid_page_time(monkeypatch, capsys) -> None:
    def fake_resolve_page_time(database_url: str, value: str) -> datetime:
        raise ValueError("invalid PostgreSQL timestamptz value")

    monkeypatch.setenv("DATABASE_URL", "postgresql://example/unused")
    monkeypatch.setattr(main_module, "resolve_page_time", fake_resolve_page_time)

    assert main_module.main(["--page-time", "bad", "json"]) == 2

    captured = capsys.readouterr()
    assert "--page-time" in captured.err


def test_main_json_subcommand_emits_json(monkeypatch, capsys) -> None:
    page_time = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setenv("DATABASE_URL", "postgresql://example/unused")
    monkeypatch.setattr(
        main_module,
        "resolve_cli_page_time",
        lambda database_url, value: page_time,
    )
    monkeypatch.setattr(
        main_module,
        "iter_lastheard_rows",
        lambda database_url, effective_page_time: iter(()),
    )
    monkeypatch.setattr(
        main_module,
        "build_page",
        lambda rows, repair_window_seconds, page_time, page_entry_limit: {
            "page_time": page_time.isoformat(),
            "page_entry_limit": page_entry_limit,
            "retained_callsign_count": 0,
            "rows_iterated": 0,
            "entries": [],
        },
    )

    assert main_module.main(["json", "--page-entry-limit", "3"]) == 0

    page = json.loads(capsys.readouterr().out)
    assert page["page_time"] == page_time.isoformat()
    assert page["page_entry_limit"] == 3


def test_main_teletext_subcommand_emits_ep1(monkeypatch, capsysbinary) -> None:
    page_time = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    calls = []

    def fake_build_page(rows, repair_window_seconds, page_time, page_entry_limit):
        calls.append((repair_window_seconds, page_entry_limit))
        return {
            "page_time": page_time.isoformat(),
            "page_entry_limit": page_entry_limit,
            "retained_callsign_count": 1,
            "rows_iterated": 1,
            "entries": [
                {
                    "type": "heard",
                    "time": "2026-06-10T12:34:00+00:00",
                    "payload": {
                        "SourceCall": "OH2DPN",
                        "ContextID": "244200",
                        "LinkCall": "OH2DMRH Pasila",
                        "DestinationID": "2442",
                        "RSSI": -109.3,
                        "BER": True,
                    },
                }
            ],
        }

    monkeypatch.setenv("DATABASE_URL", "postgresql://example/unused")
    monkeypatch.setattr(
        main_module,
        "resolve_cli_page_time",
        lambda database_url, value: page_time,
    )
    monkeypatch.setattr(
        main_module,
        "iter_lastheard_rows",
        lambda database_url, effective_page_time: iter(()),
    )
    monkeypatch.setattr(
        main_module,
        "build_page",
        fake_build_page,
    )

    assert main_module.main(
        [
            "--rssi-repair-window-seconds",
            "0",
            "teletext",
            "--subpage",
            "11/12",
        ]
    ) == 0

    output = capsysbinary.readouterr().out
    assert calls == [(0, main_module.TELETEXT_PAGE_ENTRY_LIMIT)]
    assert output.startswith(b"\xfe\x01\x18\x00\x00\x00")
    assert b"OH2DPN" in output


def test_main_teletext_subcommand_matches_ep1_fixture(
    monkeypatch,
    capsysbinary,
    set_timezone,
) -> None:
    set_timezone("Europe/Helsinki")
    fixture = Path(__file__).with_name("fixtures") / "dmr-example.ep1"
    page_time = datetime(
        2026,
        6,
        11,
        20,
        30,
        tzinfo=timezone(timedelta(hours=3)),
    )

    monkeypatch.setenv("DATABASE_URL", "postgresql://example/unused")
    monkeypatch.setattr(
        main_module,
        "resolve_page_time",
        lambda database_url, value: page_time,
    )
    monkeypatch.setattr(
        main_module,
        "iter_lastheard_rows",
        lambda database_url, effective_page_time: iter(ep1_fixture_rows()),
    )

    assert main_module.main(
        [
            "--page-time",
            "2026-06-11 20:30:00+03",
            "teletext",
            "--subpage",
            "11/12",
        ]
    ) == 0

    assert capsysbinary.readouterr().out == fixture.read_bytes()


def ep1_fixture_rows() -> list[LastHeardRow]:
    local_tz = timezone(timedelta(hours=3))
    rows = [
        ("2026-06-11T20:20:00+03:00", "OH6AAA", "OH6RAH", -43, True),
        ("2026-06-11T20:10:00+03:00", "OH3AB", "OH3DMRR", None, True),
        ("2026-06-11T20:10:00+03:00", "OH8AAA", "OH8RAO Ylivieska", -109, False),
        ("2026-06-11T19:03:00+03:00", "OH8AB", "OH8RMD Oulu 70cm", -68, False),
        ("2026-06-11T18:47:00+03:00", "OH9AAA", "OH2DMRR Raasepor", -110, False),
        ("2026-06-11T18:46:00+03:00", "OH2AAA", "OH2DMRA Porvoo", -101, False),
        ("2026-06-11T18:45:00+03:00", "OH2AAB", "OH2DMRH Pasila", -106, False),
        ("2026-06-11T18:21:00+03:00", "OH7AAA", "OH7RAA Kuopio", -120, False),
        ("2026-06-11T18:11:00+03:00", "OH2AAC", "OH2RUF", -106, False),
        ("2026-06-11T18:06:00+03:00", "OH3AAA", "OH3DMRA Lahti", -118, False),
        ("2026-06-11T18:01:00+03:00", "OH8AAC", "OH8RAO Ylivieska", -99, False),
        ("2026-06-11T17:47:00+03:00", "OH3AC", "OH3DMRR", None, False),
        ("2026-06-11T17:33:00+03:00", "OH6AAB", "OH6RUS Jämsä", -95, False),
        ("2026-06-10T23:20:00+03:00", "OH2AAD", "OH3DMRA Lahti", -109, False),
        ("2026-06-10T22:20:00+03:00", "OH6AAC", "OH8RMD Oulu 2m", -107, False),
    ]
    return [
        LastHeardRow(
            received_at=datetime.fromisoformat(received_at).astimezone(local_tz),
            payload={
                "SourceCall": callsign,
                "ContextID": "244200",
                "LinkCall": repeater,
                "RSSI": rssi,
                "BER": bool(bit_errors),
            },
        )
        for received_at, callsign, repeater, rssi, bit_errors in rows
    ]


def test_main_rejects_unknown_subcommand(capsys) -> None:
    assert main_module.main(["bad"]) == 2

    assert "usage:" in capsys.readouterr().err


def test_main_rejects_missing_subcommand(capsys) -> None:
    assert main_module.main([]) == 2

    assert "usage:" in capsys.readouterr().err
