"""One-off Neon schema inspection. Does not print secrets."""
from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
url = os.environ["CHANTIER3A_DATABASE_URL"]
conn = psycopg.connect(url, row_factory=dict_row)
cur = conn.cursor()

cur.execute(
    """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' ORDER BY table_name
    """
)
print("TABLES")
for r in cur.fetchall():
    print(r["table_name"])

print("---COLUMNS---")
cur.execute(
    """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name IN (
        'orders','ticket_types','tickets','payment_records','order_items',
        'users','org_members','events','admissions','outbound_emails','payouts'
      )
    ORDER BY table_name, ordinal_position
    """
)
for r in cur.fetchall():
    print(f"{r['table_name']}.{r['column_name']} {r['data_type']}")

print("---COUNTS---")
for t in (
    "users",
    "org_members",
    "orgs",
    "events",
    "ticket_types",
    "orders",
    "order_items",
    "tickets",
    "payment_records",
    "admissions",
    "outbound_emails",
    "payouts",
):
    cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
    print(t, cur.fetchone()["n"])

print("---EVENTS---")
cur.execute("SELECT id, slug, title, status, currency FROM events")
for r in cur.fetchall():
    print(dict(r))

print("---TICKET TYPES---")
cur.execute(
    """
    SELECT id, name, product_kind, pass_tier, price_minor, quantity_total,
           quantity_sold, status
    FROM ticket_types ORDER BY sort_order, name
    """
)
for r in cur.fetchall():
    print(dict(r))

print("---ORDER STATUS---")
cur.execute(
    """
    SELECT status, COUNT(*) AS n, COALESCE(SUM(total_minor), 0) AS total
    FROM orders GROUP BY status
    """
)
for r in cur.fetchall():
    print(dict(r))

print("---TICKET STATUS---")
cur.execute("SELECT status, COUNT(*) AS n FROM tickets GROUP BY status")
for r in cur.fetchall():
    print(dict(r))

print("---USERS ROLES---")
cur.execute(
    """
    SELECT u.email, u.name, om.role, o.slug
    FROM users u
    LEFT JOIN org_members om ON om.user_id = u.id
    LEFT JOIN orgs o ON o.id = om.org_id
    """
)
for r in cur.fetchall():
    print(dict(r))

print("---PAYMENT RECORDS---")
cur.execute(
    """
    SELECT provider, status, COUNT(*) AS n, COALESCE(SUM(amount_minor), 0) AS total
    FROM payment_records GROUP BY provider, status
    """
)
for r in cur.fetchall():
    print(dict(r))

print("---SAMPLE ORDER FLAGS---")
cur.execute(
    """
    SELECT status, currency, provider,
           (buyer_first_name <> '') AS has_fn,
           (school_name <> '') AS has_school,
           (buyer_name <> '') AS has_name
    FROM orders
    LIMIT 8
    """
)
for r in cur.fetchall():
    print(dict(r))

print("---MIGRATIONS---")
cur.execute("SELECT version FROM schema_migrations ORDER BY version")
print([r["version"] for r in cur.fetchall()])
conn.close()
