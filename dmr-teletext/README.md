# DMR Teletext

This tool reads collected BrandMeister Last Heard data from PostgreSQL and
builds the first-stage JSON data structure for a teletext page.

The `json` output emits typed timeline entries with heard rows containing
copied BrandMeister payloads, plus day markers for testing day-separator logic.
The `teletext` output renders an EP1 teletext page from that page data.

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
dmr-teletext-page-data --time '2026-06-11 17:45' json
dmr-teletext-page-data --rssi-repair-window-seconds 60 teletext --subpage 11/12 page.ep1
dmr-teletext-page-data teletext --subpage 11/12 --rssi-yellow -90 page.ep1
```

The `json` subcommand emits structured JSON for debugging. The `teletext`
subcommand emits an EP1 teletext page with 16 timeline entries. Only the `json`
subcommand accepts `--page-entry-limit`. The `teletext` subcommand requires a
5-character `--subpage` value, accepts `--rssi-yellow`, which
defaults to `-90`, and writes EP1 bytes to the required output file argument.

Global options must be placed before the subcommand. `--time` accepts a
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
