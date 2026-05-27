# bm-teletext

Tools for collecting and reporting BrandMeister DMR activity.

## Collector

The first tool lives in `collector/`. It streams BrandMeister Last Heard events,
keeps only events whose `SourceID` is a six-digit Finnish repeater/hotspot ID
from `244000` through `244999`, and appends the raw payload into PostgreSQL.

See `collector/README.md` for setup and operation.
