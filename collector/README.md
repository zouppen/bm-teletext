# BrandMeister Finnish Last Heard Collector

This collector connects to the BrandMeister Last Heard Socket.IO stream and
stores matching raw events in PostgreSQL.

The filter is intentionally narrow:

- `SourceID` must be present.
- `SourceID` must parse as a six-digit integer.
- `SourceID` must be between `244000` and `244999`, inclusive.

Seven-digit IDs beginning with `244` are rejected because Finnish amateur
station IDs are seven digits or longer, while six-digit `244xxx` IDs identify
repeaters or hotspots.

## Setup

Create a virtualenv and install the collector:

```sh
cd /work/bm-teletext/collector
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

Create the database and run the service:

```sh
export DATABASE_URL='postgresql://user:password@localhost:5432/bm_teletext'
bm-teletext-collector
```

The service creates the required table and indexes on startup.

## Configuration

Environment variables:

- `DATABASE_URL`: required PostgreSQL connection string.
- `BM_LASTHEARD_URL`: optional, defaults to `https://api.brandmeister.network`.
- `BM_LASTHEARD_SOCKETIO_PATH`: optional, defaults to `/lh/socket.io`.
- `BM_LOG_LEVEL`: optional, defaults to `INFO`.

## systemd

Copy `systemd/bm-teletext-collector.service` to `/etc/systemd/system/` and
adjust the paths, user, and `DATABASE_URL` for the target host.

## Tests

```sh
cd /work/bm-teletext/collector
pytest
```

To include PostgreSQL integration tests, set `DATABASE_URL`:

```sh
DATABASE_URL='postgresql://user:password@localhost:5432/bm_teletext_test' pytest
```
