# DMR Teletext

This tool reads collected BrandMeister Last Heard data from PostgreSQL and
builds the first-stage JSON data structure for a teletext page.

It does not render teletext yet. The current output is structured JSON so the
row processing and future squashing logic can be developed independently from
page formatting. The JSON currently emits typed timeline entries with heard
rows containing copied BrandMeister payloads, plus day markers for testing
day-separator logic.

## Setup

```sh
cd dmr-teletext
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

## Usage

```sh
export DATABASE_URL='postgresql://user:password@localhost:5432/bm_teletext'
dmr-teletext-page-data json
dmr-teletext-page-data json --page-entry-limit 50
dmr-teletext-page-data --page-time '2026-06-11 17:45' json
dmr-teletext-page-data --rssi-repair-window-seconds 60 text
dmr-teletext-page-data text
```

The `json` subcommand emits structured JSON for debugging. The `text`
subcommand emits a temporary fixed-width table for teletext layout experiments.
Only the `json` subcommand accepts `--page-entry-limit`; teletext output stays
fixed to the page template limit.

Global options must be placed before the subcommand. `--page-time` accepts a
PostgreSQL `timestamptz` value for generating a historical page. When set, only
rows with `received_at` before this time are read, and output uses this value as
`page_time`. `--rssi-repair-window-seconds` controls the maximum age difference
for repairing missing RSSI/BER from a duplicate callsign row and defaults to
`300`.

## Tests

```sh
cd dmr-teletext
pytest
```

To include PostgreSQL integration tests, set `DATABASE_URL`:

```sh
DATABASE_URL='postgresql://user:password@localhost:5432/bm_teletext_test' pytest
```
