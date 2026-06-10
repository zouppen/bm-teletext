# DMR Teletext

This tool reads collected BrandMeister Last Heard data from PostgreSQL and
builds the first-stage JSON data structure for a teletext page.

It does not render teletext yet. The current output is structured JSON so the
row processing and future squashing logic can be developed independently from
page formatting.

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
dmr-teletext-page-data
```

The page entry limit is a code constant because the final capacity depends on
the teletext template.

## Tests

```sh
cd dmr-teletext
pytest
```

To include PostgreSQL integration tests, set `DATABASE_URL`:

```sh
DATABASE_URL='postgresql://user:password@localhost:5432/bm_teletext_test' pytest
```
