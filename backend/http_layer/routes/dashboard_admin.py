"""Admin dashboard API: live Neon stats, lists, and CSV exports."""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from http_layer.deps import AppState, require_user
from http_layer.errors import json_error

log = logging.getLogger("chantier3a.admin")

router = APIRouter(prefix="/admin", tags=["admin"])

# Les inscriptions au festival sont gratuites : seul le pass explicitement
# nommé Nexus Night est payant. Un tier VIP seul ne doit pas être facturé ici.
NEXUS_SQL = "tt.name ILIKE '%%nexus%%'"
PAID_SQL = "o.status = 'paid'"
VALID_TICKET_SQL = "t.status != 'void'"


def _int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value)


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {k: _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return value


def ok(payload: Any) -> JSONResponse:
    return JSONResponse(content=jsonable_encoder(_json_value(payload)))


def _row(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return {k: _json_value(row[k]) for k in row.keys()}
    return dict(row)


def _fail(exc: Exception) -> JSONResponse:
    log.exception("admin dashboard error")
    return json_error(500, "internal_error", str(exc))


def _csv_response(filename: str, headers: list[str], rows: list[list[Any]]) -> Response:
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _table_exists(state: AppState, name: str) -> bool:
    row = state.store.fetchone(
        """
        SELECT 1 AS ok
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = ?
        """,
        (name,),
    )
    return bool(row)


def _resolve_event_id(state: AppState, id_or_slug: str) -> Optional[str]:
    row = state.store.fetchone(
        "SELECT id FROM events WHERE id = ? OR slug = ?",
        (id_or_slug, id_or_slug),
    )
    if not row:
        return None
    return row["id"]


def _display_name(row: dict[str, Any]) -> str:
    holder = (row.get("holder_name") or "").strip()
    if holder:
        return holder
    first = (row.get("buyer_first_name") or "").strip()
    last = (row.get("buyer_last_name") or "").strip()
    composed = f"{first} {last}".strip()
    if composed:
        return composed
    return (row.get("buyer_name") or "").strip() or "—"


def _participant_from_row(row: dict[str, Any]) -> dict[str, Any]:
    d = dict(row)
    d["ticket_id"] = d.get("id")
    d["name"] = _display_name(d)
    d["first_name"] = d.get("buyer_first_name") or ""
    d["last_name"] = d.get("buyer_last_name") or ""
    d["email"] = d.get("buyer_email") or ""
    d["school"] = d.get("school_name") or ""
    d["amount_minor"] = _int(d.get("total_minor"))
    d["is_nexus"] = _bool(d.get("is_nexus"))
    d["admitted"] = _bool(d.get("admitted"))
    d["has_goodies"] = _bool(d.get("has_goodies"))
    return d


@router.get("/dashboard/stats")
def get_dashboard_stats(state: AppState = Depends(require_user)):
    try:
        people = state.store.fetchone(
            """
            SELECT COUNT(DISTINCT LOWER(o.buyer_email)) AS cnt
            FROM orders o
            WHERE o.buyer_email IS NOT NULL AND o.buyer_email <> ''
            """,
            (),
        )
        paid_people = state.store.fetchone(
            f"""
            SELECT COUNT(DISTINCT LOWER(o.buyer_email)) AS cnt
            FROM orders o
            WHERE {PAID_SQL}
              AND o.buyer_email IS NOT NULL AND o.buyer_email <> ''
            """,
            (),
        )
        tickets_sold = state.store.fetchone(
            f"SELECT COUNT(*) AS cnt FROM tickets t WHERE {VALID_TICKET_SQL}",
            (),
        )
        tickets_total = state.store.fetchone(
            """
            SELECT COALESCE(SUM(quantity_total), 0) AS cnt
            FROM ticket_types
            WHERE COALESCE(product_kind, 'ticket') = 'ticket'
            """,
            (),
        )
        nexus = state.store.fetchone(
            f"""
            SELECT COUNT(t.id) AS cnt
            FROM tickets t
            JOIN ticket_types tt ON t.ticket_type_id = tt.id
            WHERE {VALID_TICKET_SQL} AND {NEXUS_SQL}
            """,
            (),
        )
        nexus_rev = state.store.fetchone(
            f"""
            SELECT COALESCE(SUM(oi.unit_price_minor * oi.quantity), 0) AS rev
            FROM order_items oi
            JOIN ticket_types tt ON oi.ticket_type_id = tt.id
            JOIN orders o ON oi.order_id = o.id
            WHERE {NEXUS_SQL} AND {PAID_SQL}
            """,
            (),
        )
        admissions = state.store.fetchone(
            "SELECT COUNT(*) AS cnt FROM admissions WHERE result = 'admitted'",
            (),
        )
        pending = state.store.fetchone(
            "SELECT COUNT(*) AS cnt FROM orders WHERE status = 'pending'",
            (),
        )
        revenue = state.store.fetchone(
            f"SELECT COALESCE(SUM(total_minor), 0) AS rev FROM orders o WHERE {PAID_SQL}",
            (),
        )
        scanned = state.store.fetchone(
            "SELECT COUNT(*) AS cnt FROM admissions",
            (),
        )
        currency_row = state.store.fetchone(
            "SELECT currency FROM orders WHERE currency IS NOT NULL AND currency <> '' LIMIT 1",
            (),
        )
        currency = (currency_row["currency"] if currency_row else None) or "XOF"

        sold = _int(tickets_sold["cnt"] if tickets_sold else 0)
        total_cap = _int(tickets_total["cnt"] if tickets_total else 0)
        admitted = _int(admissions["cnt"] if admissions else 0)

        return ok(
            {
                "participants_count": _int(people["cnt"] if people else 0),
                "paid_participants_count": _int(paid_people["cnt"] if paid_people else 0),
                "tickets_sold": sold,
                "tickets_total": total_cap,
                "nexus_night_count": _int(nexus["cnt"] if nexus else 0),
                "nexus_night_revenue_minor": _int(nexus_rev["rev"] if nexus_rev else 0),
                "admissions_count": admitted,
                "scans_total": _int(scanned["cnt"] if scanned else 0),
                "pending_orders_count": _int(pending["cnt"] if pending else 0),
                "revenue_minor": _int(revenue["rev"] if revenue else 0),
                "currency": currency,
                "scan_rate": round((admitted / sold) * 100, 1) if sold else 0,
            }
        )
    except Exception as e:
        return _fail(e)


@router.get("/analytics/registrations")
def get_analytics_registrations(
    period: str = "week",
    state: AppState = Depends(require_user),
):
    try:
        days = 7 if period == "week" else 30 if period == "month" else 90

        rows = state.store.fetchall(
            """
            WITH order_ticket_counts AS (
                SELECT
                    o.id,
                    LEFT(o.created_at, 10) AS date,
                    o.created_at,
                    o.status,
                    o.total_minor,
                    COUNT(t.id) FILTER (
                        WHERE t.status != 'void'
                    ) AS tickets
                FROM orders o
                LEFT JOIN tickets t
                    ON t.order_id = o.id
                GROUP BY
                    o.id,
                    LEFT(o.created_at, 10),
                    o.created_at,
                    o.status,
                    o.total_minor
            )
            SELECT
                date,
                COUNT(*) AS orders,
                COUNT(*) FILTER (
                    WHERE status = 'paid'
                ) AS paid_orders,
                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'paid'
                            THEN total_minor
                            ELSE 0
                        END
                    ),
                    0
                ) AS amount,
                COALESCE(SUM(tickets), 0) AS tickets
            FROM order_ticket_counts
            WHERE created_at >= TO_CHAR(
                (NOW() AT TIME ZONE 'UTC') - (? || ' days')::interval,
                'YYYY-MM-DD'
            )
            GROUP BY date
            ORDER BY date ASC
            """,
            (str(days),),
        )

        out = []

        for row in rows:
            d = _row(row)

            out.append(
                {
                    "date": d.get("date") or "",
                    "count": _int(d.get("orders")),
                    "orders": _int(d.get("orders")),
                    "tickets": _int(d.get("tickets")),
                    "amount": _int(d.get("amount")),
                }
            )

        return ok(out)

    except Exception:
        log.exception("registrations analytics fallback")

        try:
            rows = state.store.fetchall(
                """
                SELECT
                    LEFT(created_at, 10) AS date,
                    COUNT(*) AS orders,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'paid'
                                THEN total_minor
                                ELSE 0
                            END
                        ),
                        0
                    ) AS amount
                FROM orders
                GROUP BY LEFT(created_at, 10)
                ORDER BY date ASC
                """,
                (),
            )

            out = []

            for row in rows:
                d = _row(row)

                out.append(
                    {
                        "date": d.get("date") or "",
                        "count": _int(d.get("orders")),
                        "orders": _int(d.get("orders")),
                        "tickets": 0,
                        "amount": _int(d.get("amount")),
                    }
                )

            return ok(out)

        except Exception as e:
            return _fail(e)

def _participants_where(
    search: str,
    status: str,
    pass_tier: str,
    nexus: Optional[bool],
    _goodies: Optional[bool],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    args: list[Any] = []

    if search:
        clauses.append(
            """
            (
                t.holder_name ILIKE ?
                OR o.buyer_email ILIKE ?
                OR o.buyer_name ILIKE ?
                OR o.buyer_first_name ILIKE ?
                OR o.buyer_last_name ILIKE ?
                OR o.school_name ILIKE ?
                OR t.serial ILIKE ?
            )
            """
        )
        term = f"%{search}%"
        args.extend([term] * 7)

    if status:
        clauses.append("o.status = ?")
        args.append(status)

    if pass_tier:
        clauses.append("tt.pass_tier = ?")
        args.append(pass_tier)

    if nexus is True:
        clauses.append(NEXUS_SQL)
    elif nexus is False:
        clauses.append(f"NOT {NEXUS_SQL}")

    where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_str, args


_PARTICIPANT_SELECT = f"""
    SELECT
        t.id,
        t.order_id,
        t.holder_name,
        o.buyer_first_name,
        o.buyer_last_name,
        o.buyer_name,
        o.buyer_email,
        o.school_name,
        t.serial,
        tt.name AS pass_name,
        tt.pass_tier,
        o.status AS order_status,
        o.total_minor,
        o.currency,
        t.issued_at,
        ({NEXUS_SQL}) AS is_nexus,
        EXISTS(
            SELECT 1 FROM admissions a
            WHERE a.ticket_id = t.id AND a.result = 'admitted'
        ) AS admitted,
        FALSE AS has_goodies
    FROM tickets t
    JOIN orders o ON t.order_id = o.id
    JOIN ticket_types tt ON t.ticket_type_id = tt.id
"""


@router.get("/participants")
def get_participants(
    search: Optional[str] = "",
    status: Optional[str] = "",
    pass_tier: Optional[str] = "",
    nexus: Optional[bool] = None,
    goodies: Optional[bool] = None,
    page: int = 1,
    limit: int = 10,
    state: AppState = Depends(require_user),
):
    try:
        page = max(1, page)
        limit = min(max(1, limit), 10000)
        offset = (page - 1) * limit
        where_str, args = _participants_where(
            (search or "").strip(),
            (status or "").strip(),
            (pass_tier or "").strip(),
            nexus,
            goodies,
        )

        count_row = state.store.fetchone(
            f"""
            SELECT COUNT(t.id) AS cnt
            FROM tickets t
            JOIN orders o ON t.order_id = o.id
            JOIN ticket_types tt ON t.ticket_type_id = tt.id
            {where_str}
            """,
            tuple(args),
        )
        total = _int(count_row["cnt"] if count_row else 0)

        data_args = list(args)
        data_args.extend([limit, offset])
        rows = state.store.fetchall(
            f"""
            {_PARTICIPANT_SELECT}
            {where_str}
            ORDER BY t.issued_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(data_args),
        )
        return ok(
            {
                "data": [_participant_from_row(_row(r)) for r in rows],
                "total": total,
            }
        )
    except Exception as e:
        return _fail(e)


@router.get("/participants/{id}")
def get_participant(id: str, state: AppState = Depends(require_user)):
    try:
        row = state.store.fetchone(
            f"{_PARTICIPANT_SELECT} WHERE t.id = ?",
            (id,),
        )
        if not row:
            return json_error(404, "not_found", "Participant not found")
        return ok(_participant_from_row(_row(row)))
    except Exception as e:
        return _fail(e)


@router.get("/orders")
def get_orders(
    search: Optional[str] = "",
    status: Optional[str] = "",
    page: int = 1,
    limit: int = 10,
    state: AppState = Depends(require_user),
):
    try:
        page = max(1, page)
        limit = min(max(1, limit), 10000)
        offset = (page - 1) * limit
        clauses: list[str] = []
        args: list[Any] = []

        if search:
            clauses.append(
                """
                (
                    COALESCE(o.buyer_name, '') ILIKE ?
                    OR COALESCE(o.buyer_email, '') ILIKE ?
                    OR COALESCE(o.buyer_first_name, '') ILIKE ?
                    OR COALESCE(o.buyer_last_name, '') ILIKE ?
                    OR COALESCE(e.title, '') ILIKE ?
                    OR o.id ILIKE ?
                    OR COALESCE(o.provider_ref, '') ILIKE ?
                )
                """
            )
            term = f"%{search}%"
            args.extend([term] * 7)

        if status:
            clauses.append("o.status = ?")
            args.append(status)

        where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        count_row = state.store.fetchone(
            f"""
            SELECT COUNT(o.id) AS cnt
            FROM orders o
            LEFT JOIN events e ON o.event_id = e.id
            {where_str}
            """,
            tuple(args),
        )
        total = _int(count_row["cnt"] if count_row else 0)

        data_args = list(args)
        data_args.extend([limit, offset])
        rows = state.store.fetchall(
            f"""
            SELECT
                o.id,
                o.event_id,
                o.buyer_name,
                o.buyer_email,
                o.buyer_first_name,
                o.buyer_last_name,
                o.school_name,
                o.status,
                o.subtotal_minor,
                o.total_minor,
                o.currency,
                o.provider,
                o.provider_ref,
                o.created_at,
                o.paid_at,
                e.title AS event_title
            FROM orders o
            LEFT JOIN events e ON o.event_id = e.id
            {where_str}
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(data_args),
        )
        data = []
        for row in rows:
            d = _row(row)
            if not (d.get("buyer_name") or "").strip():
                d["buyer_name"] = f"{d.get('buyer_first_name') or ''} {d.get('buyer_last_name') or ''}".strip()
            data.append(d)
        return ok({"data": data, "total": total})
    except Exception as e:
        return _fail(e)


@router.get("/orders/{id}")
def get_order(id: str, state: AppState = Depends(require_user)):
    try:
        row = state.store.fetchone(
            """
            SELECT o.*, e.title AS event_title
            FROM orders o
            LEFT JOIN events e ON o.event_id = e.id
            WHERE o.id = ?
            """,
            (id,),
        )
        if not row:
            return json_error(404, "not_found", "Order not found")
        d = _row(row)
        if not (d.get("buyer_name") or "").strip():
            d["buyer_name"] = f"{d.get('buyer_first_name') or ''} {d.get('buyer_last_name') or ''}".strip()
        items = state.store.fetchall(
            """
            SELECT oi.*, tt.name AS ticket_type_name, tt.pass_tier, tt.product_kind
            FROM order_items oi
            LEFT JOIN ticket_types tt ON oi.ticket_type_id = tt.id
            WHERE oi.order_id = ?
            """,
            (id,),
        )
        d["items"] = [_row(item) for item in items]
        tickets = state.store.fetchall(
            """
            SELECT id, serial, holder_name, status, issued_at
            FROM tickets WHERE order_id = ?
            """,
            (id,),
        )
        d["tickets"] = [_row(t) for t in tickets]
        return ok(d)
    except Exception as e:
        return _fail(e)


@router.get("/tickets")
def get_tickets(
    search: Optional[str] = "",
    status: Optional[str] = "",
    state: AppState = Depends(require_user),
):
    try:
        clauses: list[str] = []
        args: list[Any] = []
        if search:
            clauses.append("(t.serial ILIKE ? OR t.holder_name ILIKE ? OR o.buyer_email ILIKE ?)")
            term = f"%{search}%"
            args.extend([term, term, term])
        if status:
            clauses.append("t.status = ?")
            args.append(status)
        where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = state.store.fetchall(
            f"""
            SELECT
                t.*,
                tt.name AS type_name,
                o.buyer_email,
                o.buyer_name
            FROM tickets t
            JOIN ticket_types tt ON t.ticket_type_id = tt.id
            JOIN orders o ON t.order_id = o.id
            {where_str}
            ORDER BY t.issued_at DESC
            LIMIT 500
            """,
            tuple(args),
        )
        out = []
        for row in rows:
            d = _row(row)
            d["ticket_type"] = {"name": d.get("type_name")}
            out.append(d)
        return ok(out)
    except Exception as e:
        return _fail(e)


@router.post("/tickets/{serial}/void")
def void_ticket(serial: str, state: AppState = Depends(require_user)):
    try:
        row = state.store.fetchone("SELECT * FROM tickets WHERE serial = ?", (serial,))
        if not row:
            return json_error(404, "not_found", "Ticket not found")
        if row["status"] == "void":
            return ok({"status": "ok", "message": "Already voided"})
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        state.store.execute(
            "UPDATE tickets SET status = 'void', voided_at = ? WHERE serial = ?",
            (now, serial),
        )
        return ok({"status": "ok"})
    except Exception as e:
        return _fail(e)


@router.get("/events")
def get_events(state: AppState = Depends(require_user)):
    try:
        rows = state.store.fetchall(
            """
            SELECT e.*,
                (SELECT COUNT(*) FROM tickets WHERE event_id = e.id AND status != 'void') AS tickets_sold
            FROM events e
            ORDER BY e.created_at DESC
            """,
            (),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/events/{id_or_slug}")
def get_event(id_or_slug: str, state: AppState = Depends(require_user)):
    try:
        row = state.store.fetchone(
            "SELECT * FROM events WHERE id = ? OR slug = ?",
            (id_or_slug, id_or_slug),
        )
        if not row:
            return json_error(404, "not_found", "Event not found")
        return ok(_row(row))
    except Exception as e:
        return _fail(e)


@router.get("/events/{event_id}/ticket-types")
def get_event_ticket_types(event_id: str, state: AppState = Depends(require_user)):
    try:
        resolved = _resolve_event_id(state, event_id)
        if not resolved:
            return json_error(404, "not_found", "Event not found")
        rows = state.store.fetchall(
            """
            SELECT * FROM ticket_types
            WHERE event_id = ?
            ORDER BY sort_order ASC, name ASC
            """,
            (resolved,),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/admissions")
def get_admissions(
    search: Optional[str] = "",
    result: Optional[str] = "",
    state: AppState = Depends(require_user),
):
    try:
        clauses: list[str] = []
        args: list[Any] = []
        if result:
            clauses.append("a.result = ?")
            args.append(result)
        if search:
            clauses.append("(t.serial ILIKE ? OR t.holder_name ILIKE ? OR a.gate_id ILIKE ?)")
            term = f"%{search}%"
            args.extend([term, term, term])
        where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = state.store.fetchall(
            f"""
            SELECT
                a.*,
                t.serial,
                t.holder_name,
                tt.name AS pass_name,
                e.title AS event_title
            FROM admissions a
            LEFT JOIN tickets t ON a.ticket_id = t.id
            LEFT JOIN ticket_types tt ON t.ticket_type_id = tt.id
            LEFT JOIN events e ON a.event_id = e.id
            {where_str}
            ORDER BY a.scanned_at DESC
            LIMIT 500
            """,
            tuple(args),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/users")
def get_users(state: AppState = Depends(require_user)):
    try:
        rows = state.store.fetchall(
            """
            SELECT
                u.id,
                u.email,
                u.name,
                u.created_at,
                m.role AS org_role
            FROM users u
            LEFT JOIN org_members m ON u.id = m.user_id
            ORDER BY u.created_at DESC
            LIMIT 100
            """,
            (),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/outbound-emails")
def get_outbound_emails(state: AppState = Depends(require_user)):
    try:
        if not _table_exists(state, "outbound_emails"):
            return ok([])
        rows = state.store.fetchall(
            "SELECT * FROM outbound_emails ORDER BY created_at DESC LIMIT 100",
            (),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/payments")
def get_payments(state: AppState = Depends(require_user)):
    try:
        rows = state.store.fetchall(
            """
            SELECT
                p.provider,
                p.reference,
                p.amount_minor,
                p.currency,
                p.status,
                p.instructions,
                p.marked_by,
                p.marked_at,
                p.created_at,
                p.updated_at,
                o.buyer_email,
                o.total_minor,
                o.id AS order_id
            FROM payment_records p
            LEFT JOIN orders o
                ON o.provider_ref = p.reference OR o.id = p.reference
            ORDER BY p.created_at DESC
            LIMIT 200
            """,
            (),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/payouts")
def get_payouts(state: AppState = Depends(require_user)):
    try:
        if not _table_exists(state, "payouts"):
            return ok([])
        rows = state.store.fetchall(
            "SELECT * FROM payouts ORDER BY created_at DESC LIMIT 100",
            (),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/sync/peers")
def get_sync_peers(state: AppState = Depends(require_user)):
    try:
        if not _table_exists(state, "sync_peer"):
            return ok([])
        rows = state.store.fetchall("SELECT * FROM sync_peer ORDER BY name ASC", ())
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/notifications")
def get_notifications(state: AppState = Depends(require_user)):
    try:
        if not _table_exists(state, "notifications"):
            return ok([])
        rows = state.store.fetchall(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50",
            (),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.post("/notifications/{id}/read")
def read_notification(id: str, state: AppState = Depends(require_user)):
    try:
        if not _table_exists(state, "notifications"):
            return ok({"status": "ok"})
        state.store.execute("UPDATE notifications SET unread = false WHERE id = ?", (id,))
        return ok({"status": "ok"})
    except Exception as e:
        return _fail(e)


@router.post("/notifications/mark-all-read")
def mark_all_read_notifications(state: AppState = Depends(require_user)):
    try:
        if not _table_exists(state, "notifications"):
            return ok({"status": "ok"})
        state.store.execute("UPDATE notifications SET unread = false", ())
        return ok({"status": "ok"})
    except Exception as e:
        return _fail(e)


@router.get("/events-log")
def get_events_log(state: AppState = Depends(require_user)):
    try:
        if not _table_exists(state, "events_log"):
            return ok([])
        rows = state.store.fetchall(
            "SELECT * FROM events_log ORDER BY created_at DESC LIMIT 100",
            (),
        )
        return ok([_row(r) for r in rows])
    except Exception as e:
        return _fail(e)


@router.get("/exports/participants.csv")
def export_participants_csv(
    nexus: Optional[bool] = None,
    state: AppState = Depends(require_user),
):
    try:
        where_str, args = _participants_where("", "", "", nexus, None)
        rows = state.store.fetchall(
            f"{_PARTICIPANT_SELECT} {where_str} ORDER BY t.issued_at DESC LIMIT 20000",
            tuple(args),
        )
        headers = [
            "Billet",
            "Nom",
            "Prenom",
            "Nom_famille",
            "Email",
            "Ecole",
            "Pass",
            "Tier",
            "Statut",
            "Nexus_Night",
            "Scanne",
            "Date",
        ]
        body = []
        for row in rows:
            p = _participant_from_row(_row(row))
            body.append(
                [
                    p.get("serial"),
                    p.get("name"),
                    p.get("first_name"),
                    p.get("last_name"),
                    p.get("email"),
                    p.get("school"),
                    p.get("pass_name"),
                    p.get("pass_tier"),
                    p.get("order_status"),
                    "OUI" if p.get("is_nexus") else "NON",
                    "OUI" if p.get("admitted") else "NON",
                    p.get("issued_at"),
                ]
            )
        name = "tdev_nexus_night.csv" if nexus else "tdev_participants.csv"
        return _csv_response(name, headers, body)
    except Exception as e:
        return _fail(e)


@router.get("/exports/orders.csv")
def export_orders_csv(state: AppState = Depends(require_user)):
    try:
        rows = state.store.fetchall(
            """
            SELECT o.*, e.title AS event_title
            FROM orders o
            LEFT JOIN events e ON o.event_id = e.id
            ORDER BY o.created_at DESC
            LIMIT 20000
            """,
            (),
        )
        headers = [
            "Commande",
            "Nom",
            "Email",
            "Ecole",
            "Statut",
            "Montant",
            "Devise",
            "Fournisseur",
            "Reference",
            "Cree_le",
            "Paye_le",
        ]
        body = []
        for row in rows:
            d = _row(row)
            name = (d.get("buyer_name") or "").strip() or f"{d.get('buyer_first_name') or ''} {d.get('buyer_last_name') or ''}".strip()
            body.append(
                [
                    d.get("id"),
                    name,
                    d.get("buyer_email"),
                    d.get("school_name"),
                    d.get("status"),
                    d.get("total_minor"),
                    d.get("currency"),
                    d.get("provider"),
                    d.get("provider_ref"),
                    d.get("created_at"),
                    d.get("paid_at"),
                ]
            )
        return _csv_response("tdev_commandes.csv", headers, body)
    except Exception as e:
        return _fail(e)


@router.get("/exports/tickets.csv")
def export_tickets_csv(state: AppState = Depends(require_user)):
    try:
        rows = state.store.fetchall(
            """
            SELECT t.serial, t.holder_name, t.status, t.issued_at, t.voided_at,
                   tt.name AS type_name, o.buyer_email
            FROM tickets t
            JOIN ticket_types tt ON t.ticket_type_id = tt.id
            JOIN orders o ON t.order_id = o.id
            ORDER BY t.issued_at DESC
            LIMIT 20000
            """,
            (),
        )
        headers = ["Serie", "Detenteur", "Pass", "Email", "Statut", "Emis_le", "Annule_le"]
        body = [
            [
                _row(r).get("serial"),
                _row(r).get("holder_name"),
                _row(r).get("type_name"),
                _row(r).get("buyer_email"),
                _row(r).get("status"),
                _row(r).get("issued_at"),
                _row(r).get("voided_at"),
            ]
            for r in rows
        ]
        return _csv_response("tdev_billets.csv", headers, body)
    except Exception as e:
        return _fail(e)


@router.get("/exports/admissions.csv")
def export_admissions_csv(state: AppState = Depends(require_user)):
    try:
        rows = state.store.fetchall(
            """
            SELECT a.id, a.result, a.gate_id, a.device_id, a.note, a.scanned_at,
                   t.serial, t.holder_name, tt.name AS pass_name
            FROM admissions a
            LEFT JOIN tickets t ON a.ticket_id = t.id
            LEFT JOIN ticket_types tt ON t.ticket_type_id = tt.id
            ORDER BY a.scanned_at DESC
            LIMIT 20000
            """,
            (),
        )
        headers = ["Scan", "Billet", "Detenteur", "Pass", "Portique", "Appareil", "Resultat", "Note", "Date"]
        body = [
            [
                _row(r).get("id"),
                _row(r).get("serial"),
                _row(r).get("holder_name"),
                _row(r).get("pass_name"),
                _row(r).get("gate_id"),
                _row(r).get("device_id"),
                _row(r).get("result"),
                _row(r).get("note"),
                _row(r).get("scanned_at"),
            ]
            for r in rows
        ]
        return _csv_response("tdev_scans.csv", headers, body)
    except Exception as e:
        return _fail(e)
