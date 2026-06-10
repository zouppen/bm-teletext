from __future__ import annotations

import json
import os
import sys

from dmr_teletext.db import iter_lastheard_rows
from dmr_teletext.page_data import build_page


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    page = build_page(iter_lastheard_rows(database_url))
    print(json.dumps(page, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
