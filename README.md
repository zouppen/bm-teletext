# bm-teletext

Tools for collecting and reporting BrandMeister DMR activity.

## Collector

The first tool lives in `collector/`. It streams BrandMeister Last Heard events,
keeps only events whose wire `ContextID` begins with `244`, and appends the raw
payload into PostgreSQL.

See `collector/README.md` for setup and operation.
