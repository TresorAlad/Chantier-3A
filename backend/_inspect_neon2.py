"""Inspect extra Neon objects without printing secrets or PII payloads."""
from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
conn = psycopg.connect(os.environ["CHANTIER3A_DATABASE_URL"], row_factory=dict_row)
cur = conn.cursor()

print("---MIGRATION NAMES---")
cur.execute("SELECT version, name FROM schema_migrations ORDER BY version")
for r in cur.fetchall():
    print(r["version"], r["name"])

print("---EXTRA TABLE COLUMNS---")
cur.execute(
    """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name IN ('notifications', 'events_log', 'system_settings', 'users')
    ORDER BY table_name, ordinal_position
    """
)
for r in cur.fetchall():
    print(f"{r['table_name']}.{r['column_name']} {r['data_type']}")

print("---SCHEMAS---")
cur.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
print([r["schema_name"] for r in cur.fetchall()])

print("---ROW COUNTS ALL---")
cur.execute(
    """
    SELECT relname, n_live_tup
    FROM pg_stat_user_tables
    ORDER BY n_live_tup DESC, relname
    """
)
for r in cur.fetchall():
    print(r["relname"], r["n_live_tup"])

print("---ORGS---")
cur.execute("SELECT id, name, slug, default_currency FROM orgs")
for r in cur.fetchall():
    print(dict(r))

print("---SETTINGS---")
cur.execute("SELECT key FROM system_settings")
print([r["key"] for r in cur.fetchall()])

print("---NOTIF COUNT---")
cur.execute("SELECT COUNT(*) AS n FROM notifications")
print(cur.fetchone()["n"])
cur.execute("SELECT COUNT(*) AS n FROM events_log")
print("events_log", cur.fetchone()["n"])
conn.close()
