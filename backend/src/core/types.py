"""Dialect-portable column types.

The models were written against `sqlalchemy.dialects.postgresql` types, which is
correct for production and unusable for the in-memory SQLite database the
integration tests run on. Two failures came from it:

* `JSONB` cannot be rendered by the SQLite compiler at all, so the entire
  schema was uncreatable (fixed in `failure_layer/models.py`).
* `postgresql.UUID` degrades to CHAR(32) on SQLite but does **not** convert
  values back to `uuid.UUID` on read, so a round-tripped id comes back as a
  `str` and the next query against it fails with
  `'str' object has no attribute 'hex'` — deep inside the driver, far from the
  cause.

`sqlalchemy.Uuid` is the generic type introduced for exactly this: it emits the
backend's native UUID on PostgreSQL and a correctly round-tripping CHAR(32)
everywhere else. Nothing about production behaviour changes.

Import column types from here rather than from a dialect module.
"""

from __future__ import annotations

from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB

#: Native `uuid` on PostgreSQL, round-tripping CHAR(32) elsewhere.
#: Drop-in for `postgresql.UUID` — same `as_uuid=` keyword.
UUID = Uuid

#: `JSONB` on PostgreSQL, plain `JSON` elsewhere.
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")

__all__ = ["UUID", "JSON_TYPE"]
