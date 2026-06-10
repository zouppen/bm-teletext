# bm-teletext

Tools for collecting and reporting BrandMeister DMR activity.

## Collector

The first tool lives in `bm-collector/`. It streams BrandMeister Last Heard events,
keeps only events whose wire `ContextID` begins with `244`, and appends the raw
payload into PostgreSQL.

See `bm-collector/README.md` for setup and operation.

## DMR Teletext

The teletext data generator lives in `dmr-teletext/`. It reads collected DMR
activity from PostgreSQL and emits first-stage JSON page data.

See `dmr-teletext/README.md` for setup and operation.
