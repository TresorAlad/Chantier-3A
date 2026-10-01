"""The existing 3A application, served alone, as the "before" reference of the load tests.

    CHECKIN_LOAD_DATABASE_URL=postgresql://... \
    uvicorn --app-dir tests/load legacy_app:app --port 8091

Equivalent to ``billetterie-api serve --demo``. ``LEGACY_DISABLE_RATE_LIMIT=1`` lifts the 3A limiter
(120 requests/min per IP on ``/api/scan*``), which a single load generator would otherwise hit at once;
this is a MEASUREMENT harness only and nothing in the 3A code is changed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bootstrap import build_services  # noqa: E402
from config import load_config  # noqa: E402
from http_layer.app import create_app  # noqa: E402
from http_layer.middleware import rate_limit  # noqa: E402
from store.store import open_postgres  # noqa: E402

url = os.environ["CHECKIN_LOAD_DATABASE_URL"]
if os.environ.get("LEGACY_DISABLE_RATE_LIMIT") == "1":
    rate_limit.ScanRateLimitMiddleware.__init__.__kwdefaults__["max_requests"] = 10**9

_store = open_postgres(url)
_cfg = load_config(database_url=url, demo=True)
app = create_app(_store, _cfg, build_services(_store, _cfg))
