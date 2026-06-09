# BrandMeister Finnish Last Heard Collector

This collector connects to the BrandMeister Last Heard Socket.IO stream and
stores matching raw events in PostgreSQL.

The default filter is intentionally narrow:

- `ContextID` must be present in the BrandMeister wire payload.
- `ContextID` is converted with plain `str(value)`.
- The string is searched with the regex `^244`.

BrandMeister's web table labels this repeater/link field as "Source", but the
wire payload field used by the collector is `ContextID`. That default accepts
ContextID values beginning with `244`. Override `BM_CONTEXT_ID_PATTERN` to use a
different regular expression.

## Setup

Create a virtualenv and install the collector:

```sh
cd /work/bm-collector
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

Create the database and run the service:

```sh
export DATABASE_URL='postgresql://user:password@localhost:5432/bm_teletext'
bm-collector
```

The service creates the required table and indexes on startup.

## Configuration

Environment variables:

- `DATABASE_URL`: required PostgreSQL connection string.
- `BM_LASTHEARD_URL`: optional, defaults to `https://api.brandmeister.network`.
- `BM_LASTHEARD_SOCKETIO_PATH`: optional, defaults to `/lh`.
- `BM_CONTEXT_ID_PATTERN`: optional, defaults to `^244`.
- `BM_LOG_LEVEL`: optional, defaults to `INFO`.

## systemd

Copy `systemd/bm-collector.service` to `/etc/systemd/system/` and
adjust the paths, user, and `DATABASE_URL` for the target host.

## Tests

```sh
cd /work/bm-collector
pytest
```

To include PostgreSQL integration tests, set `DATABASE_URL`:

```sh
DATABASE_URL='postgresql://user:password@localhost:5432/bm_teletext_test' pytest
```
