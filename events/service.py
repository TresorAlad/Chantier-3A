"""Event lifecycle, ticket types, and organizer-facing operations."""

from __future__ import annotations

import base64
from datetime import datetime, timezone

from config import Config, HostScope
from money import currency as money
from store import NotFoundError, Store
from store import event_keys as event_keys_repo
from store import events_repo, orgs, ticket_types as tt_repo
from store.events_repo import EventRow
from store.store import new_ulid
from store.timeutil import time_to_text
from events import passes as pass_catalog
from tickets import capability as cap


class EventsError(Exception):
    """Eventserror."""
    pass


class InvalidInput(EventsError):
    """Invalidinput."""
    pass


class InvalidTransition(EventsError):
    """Invalidtransition."""
    pass


class QuantityBelowSold(EventsError):
    """Quantitybelowsold."""
    pass


class TicketTypeHasSales(EventsError):
    """Tickettypehassales."""
    pass


class EventHasTickets(EventsError):
    """Eventhastickets."""
    pass


def event_to_json(e: EventRow) -> dict:
    """Event to json."""
    out: dict = {
        "id": e.id,
        "org_id": e.org_id,
        "slug": e.slug,
        "title": e.title,
        "summary": e.summary,
        "description": e.description,
        "venue_name": e.venue_name,
        "address": e.address,
        "starts_at": e.starts_at.isoformat().replace("+00:00", "Z"),
        "ends_at": e.ends_at.isoformat().replace("+00:00", "Z"),
        "timezone": e.timezone,
        "cover_image": e.cover_image,
        "status": e.status,
        "currency": e.currency,
        "category": e.category,
        "created_at": e.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": e.updated_at.isoformat().replace("+00:00", "Z"),
    }
    if e.lat is not None:
        out["lat"] = e.lat
    if e.lng is not None:
        out["lng"] = e.lng
    if e.cover_image_id:
        out["cover_image_id"] = e.cover_image_id
    return out


def ticket_type_to_json(tt: tt_repo.TicketType) -> dict:
    """Ticket type to json."""
    out: dict = {
        "id": tt.id,
        "event_id": tt.event_id,
        "name": tt.name,
        "description": tt.description,
        "price_minor": tt.price_minor,
        "quantity_total": tt.quantity_total,
        "quantity_sold": tt.quantity_sold,
        "max_per_order": tt.max_per_order,
        "status": tt.status,
        "sort_order": tt.sort_order,
        "product_kind": tt.product_kind,
    }
    if tt.pass_tier:
        out["pass_tier"] = tt.pass_tier
    if tt.sales_start:
        out["sales_start"] = tt.sales_start.isoformat().replace("+00:00", "Z")
    if tt.sales_end:
        out["sales_end"] = tt.sales_end.isoformat().replace("+00:00", "Z")
    return out


def issuer_keys_json(st: Store, event_id: str) -> dict:
    """Issuer keys json."""
    ring = cap.KeyRing.new(event_id)
    for ek in event_keys_repo.active_event_keys(st, event_id):
        kid = cap.key_id(ek.public_key)
        ring.add(kid, ek.public_key)
    keys_b64: dict[str, str] = {}
    for kid, pub in ring.keys.items():
        keys_b64[kid] = base64.urlsafe_b64encode(pub).decode().rstrip("=")
    return {"event_id": event_id, "keys": keys_b64}


def normalize_category(c: str) -> str:
    """Normalize category."""
    c = c.strip().lower()
    parts: list[str] = []
    prev_hyphen = False
    for ch in c:
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            parts.append(ch)
            prev_hyphen = False
        elif not prev_hyphen and parts:
            parts.append("-")
            prev_hyphen = True
    out = "".join(parts).rstrip("-")
    return out


def host_scope(st: Store, cfg: Config) -> tuple[HostScope, list[dict], list[str]]:
    """Host scope."""
    scope: HostScope = cfg.host_scope
    all_orgs = orgs.list_public_host_orgs(st)
    views = [{"id": o.id, "name": o.name, "slug": o.slug} for o in all_orgs]

    if scope == "single":
        ref = cfg.host_org
        if not ref:
            return scope, [], []
        try:
            org = orgs.get_org_by_slug(st, ref)
        except NotFoundError:
            try:
                org = orgs.get_org_by_id(st, ref)
            except NotFoundError:
                raise RuntimeError("CHANTIER3A_HOST_ORG names no organisation on this host")
        views = [{"id": org.id, "name": org.name, "slug": org.slug}]
        return scope, views, [org.id]

    org_ids = [o.id for o in all_orgs]
    return scope, views, org_ids


def host_display_name(cfg: Config, scope: HostScope, org_views: list[dict]) -> str:
    """Host display name."""
    if cfg.host_name:
        return cfg.host_name
    if scope == "single" and org_views:
        return org_views[0]["name"]
    return ""


def list_public(
    st: Store,
    cfg: Config,
    *,
    query: str,
    category: str,
    org_ids: list[str] | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
    limit: int,
) -> list[dict]:
    """List public."""
    rows = events_repo.list_published_events(
        st, query, normalize_category(category), org_ids, from_ts, to_ts, limit
    )
    return [event_to_json(e) for e in rows]


def get(st: Store, event_id: str) -> dict:
    """Get."""
    return event_to_json(events_repo.get_event_by_id(st, event_id))


def get_by_slug_or_id(st: Store, ref: str) -> dict:
    """Get by slug or id."""
    try:
        return event_to_json(events_repo.get_event_by_slug(st, ref))
    except NotFoundError:
        return get(st, ref)


def list_by_org(st: Store, org_id: str) -> list[dict]:
    """List by org."""
    rows = events_repo.list_events_by_org(st, org_id)
    return [event_to_json(e) for e in rows]


def create(
    st: Store,
    org_id: str,
    body: dict,
) -> dict:
    """Create."""
    if not org_id.strip():
        raise InvalidInput("org id is required")
    slug = (body.get("slug") or "").strip()
    title = (body.get("title") or "").strip()
    if not slug:
        raise InvalidInput("slug is required")
    if not title:
        raise InvalidInput("title is required")
    starts = _parse_time_field(body.get("starts_at"))
    ends = _parse_time_field(body.get("ends_at"))
    if starts is None or ends is None:
        raise InvalidInput("starts_at and ends_at are required")
    if ends <= starts:
        raise InvalidInput("ends_at must be after starts_at")

    try:
        org = orgs.get_org_by_id(st, org_id)
    except NotFoundError as err:
        raise NotFoundError() from err

    currency = (body.get("currency") or "").strip() or org.default_currency
    try:
        currency = money.normalize(currency)
    except money.CurrencyError as err:
        raise InvalidInput(f"currency: {err}") from err

    now = datetime.now(timezone.utc)
    event_id = new_ulid()
    pub, priv = event_keys_repo.generate_ed25519_keypair()
    row = {
        "id": event_id,
        "org_id": org_id,
        "slug": slug,
        "title": title,
        "summary": body.get("summary") or "",
        "description": body.get("description") or "",
        "venue_name": body.get("venue_name") or "",
        "address": body.get("address") or "",
        "lat": body.get("lat"),
        "lng": body.get("lng"),
        "starts_at": time_to_text(starts),
        "ends_at": time_to_text(ends),
        "timezone": (body.get("timezone") or "").strip() or "UTC",
        "cover_image": body.get("cover_image") or "",
        "status": "draft",
        "currency": currency,
        "category": normalize_category(body.get("category") or ""),
    }
    event_keys_repo.create_event_with_key(st, row, pub, priv)
    return get(st, event_id)


def update(st: Store, event_id: str, body: dict) -> dict:
    """Update."""
    e = events_repo.get_event_by_id(st, event_id)
    if "slug" in body and body["slug"] is not None:
        if not str(body["slug"]).strip():
            raise InvalidInput("slug cannot be empty")
        e.slug = str(body["slug"]).strip()
    if "title" in body and body["title"] is not None:
        if not str(body["title"]).strip():
            raise InvalidInput("title cannot be empty")
        e.title = str(body["title"]).strip()
    for field in ("summary", "description", "venue_name", "address", "timezone", "cover_image"):
        if field in body and body[field] is not None:
            setattr(e, field, body[field])
    if "lat" in body:
        e.lat = body["lat"]
    if "lng" in body:
        e.lng = body["lng"]
    if "starts_at" in body and body["starts_at"] is not None:
        e.starts_at = _parse_time_field(body["starts_at"]) or e.starts_at
    if "ends_at" in body and body["ends_at"] is not None:
        e.ends_at = _parse_time_field(body["ends_at"]) or e.ends_at
    if "currency" in body and body["currency"] is not None:
        try:
            e.currency = money.normalize(str(body["currency"]))
        except money.CurrencyError as err:
            raise InvalidInput(f"currency: {err}") from err
    if "category" in body and body["category"] is not None:
        e.category = normalize_category(str(body["category"]))
    if "status" in body and body["status"] is not None:
        if body["status"] != "cancelled":
            raise InvalidTransition('use Publish to publish; Update may only set status to "cancelled"')
        e.status = "cancelled"
    if e.ends_at <= e.starts_at:
        raise InvalidInput("ends_at must be after starts_at")
    e.updated_at = datetime.now(timezone.utc)
    events_repo.update_event(st, e)
    return get(st, event_id)


def publish(st: Store, event_id: str) -> dict:
    """Publish."""
    e = events_repo.get_event_by_id(st, event_id)
    if e.status == "published":
        return event_to_json(e)
    if e.status != "draft":
        raise InvalidTransition(f"cannot publish an event with status {e.status!r}")
    now = datetime.now(timezone.utc)
    events_repo.set_event_status(st, event_id, "published", now)
    e.status = "published"
    e.updated_at = now
    return event_to_json(e)


def delete_event(st: Store, event_id: str) -> None:
    """Delete event."""
    events_repo.get_event_by_id(st, event_id)
    n = events_repo.count_tickets_for_event(st, event_id)
    if n > 0:
        raise EventHasTickets(f"cannot delete an event with issued tickets ({n})")
    events_repo.delete_event(st, event_id)


def stats(st: Store, event_id: str) -> dict:
    """Stats."""
    events_repo.get_event_by_id(st, event_id)
    rows = events_repo.ticket_type_stats_for_event(st, event_id)
    admitted = events_repo.count_admitted_for_event(st, event_id)
    sold = 0
    revenue = 0
    by_type: list[dict] = []
    for r in rows:
        sold += r.sold
        revenue += r.revenue_minor
        by_type.append(
            {
                "ticket_type_id": r.ticket_type_id,
                "name": r.name,
                "quantity_total": r.quantity_total,
                "sold": r.sold,
                "revenue_minor": r.revenue_minor,
            }
        )
    return {"sold": sold, "revenue_minor": revenue, "admitted": admitted, "by_type": by_type}


def list_ticket_types(st: Store, event_id: str) -> list[dict]:
    """List ticket types."""
    return [ticket_type_to_json(t) for t in tt_repo.list_ticket_types_for_event(st, event_id)]


def _validate_ticket_type_input(body: dict, *, existing: tt_repo.TicketType | None = None) -> None:
    """Internal: validate ticket type input."""
    if existing is None and not str(body.get("name") or "").strip():
        raise InvalidInput("name is required")
    if "name" in body and not str(body.get("name") or "").strip():
        raise InvalidInput("name is required")
    default_price = existing.price_minor if existing else 0
    price = int(body.get("price_minor", default_price))
    if price < 0:
        raise InvalidInput("price_minor cannot be negative")
    qty_default = existing.quantity_total if existing else 0
    if int(body.get("quantity_total", qty_default)) < 0:
        raise InvalidInput("quantity_total cannot be negative")
    max_default = existing.max_per_order if existing else 0
    if int(body.get("max_per_order", max_default)) < 0:
        raise InvalidInput("max_per_order cannot be negative")
    if "pass_tier" in body:
        tier = pass_catalog.normalize_pass_tier(body.get("pass_tier"))
    elif existing is not None:
        tier = existing.pass_tier
    else:
        tier = pass_catalog.normalize_pass_tier(body.get("pass_tier"))
    if tier is not None:
        if tier not in pass_catalog.ALL_PASS_TIERS:
            raise InvalidInput("pass_tier must be student, standard, or vip")
        if tier not in pass_catalog.ENABLED_PASS_TIERS:
            raise InvalidInput("this pass tier is not available yet")
        if tier == pass_catalog.PASS_TIER_STUDENT and price != 0:
            raise InvalidInput("student pass must be free (price_minor 0)")


def create_ticket_type(st: Store, event_id: str, body: dict) -> dict:
    """Create ticket type."""
    _validate_ticket_type_input(body)
    events_repo.get_event_by_id(st, event_id)
    tt = tt_repo.TicketType(
        id=new_ulid(),
        event_id=event_id,
        name=str(body["name"]).strip(),
        description=body.get("description") or "",
        price_minor=int(body.get("price_minor", 0)),
        quantity_total=int(body.get("quantity_total", 0)),
        quantity_sold=0,
        sales_start=_parse_time_field(body.get("sales_start")),
        sales_end=_parse_time_field(body.get("sales_end")),
        max_per_order=int(body.get("max_per_order", 0) or 10),
        status=(body.get("status") or "active").strip() or "active",
        sort_order=int(body.get("sort_order", 0)),
        product_kind=(body.get("product_kind") or tt_repo.PRODUCT_KIND_TICKET).strip()
        or tt_repo.PRODUCT_KIND_TICKET,
        pass_tier=pass_catalog.normalize_pass_tier(body.get("pass_tier")),
    )
    tt_repo.create_ticket_type(st, tt)
    return ticket_type_to_json(tt)


def update_ticket_type(st: Store, tt_id: str, body: dict) -> dict:
    """Update ticket type."""
    existing = tt_repo.get_ticket_type_by_id(st, tt_id)
    _validate_ticket_type_input(body, existing=existing)
    qty = int(body.get("quantity_total", existing.quantity_total))
    if qty < existing.quantity_sold:
        raise QuantityBelowSold(f"{qty} < {existing.quantity_sold} already sold")
    tt = tt_repo.TicketType(
        id=existing.id,
        event_id=existing.event_id,
        name=str(body["name"]).strip(),
        description=body.get("description") or "",
        price_minor=int(body.get("price_minor", existing.price_minor)),
        quantity_total=qty,
        quantity_sold=existing.quantity_sold,
        sales_start=_parse_time_field(body.get("sales_start")) if "sales_start" in body else existing.sales_start,
        sales_end=_parse_time_field(body.get("sales_end")) if "sales_end" in body else existing.sales_end,
        max_per_order=int(body.get("max_per_order", existing.max_per_order)),
        status=(body.get("status") or existing.status).strip() or "active",
        sort_order=int(body.get("sort_order", existing.sort_order)),
        product_kind=(body.get("product_kind") or existing.product_kind).strip() or existing.product_kind,
        pass_tier=(
            pass_catalog.normalize_pass_tier(body["pass_tier"])
            if "pass_tier" in body
            else existing.pass_tier
        ),
    )
    tt_repo.update_ticket_type(st, tt)
    return ticket_type_to_json(tt)


def delete_ticket_type(st: Store, tt_id: str) -> None:
    """Delete ticket type."""
    tt = tt_repo.get_ticket_type_by_id(st, tt_id)
    if tt.quantity_sold > 0:
        raise TicketTypeHasSales(f"{tt.quantity_sold} sold/reserved")
    tt_repo.delete_ticket_type(st, tt_id)


def _parse_time_field(value) -> datetime | None:
    """Internal: parse time field."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def category_label(slug: str) -> str:
    """Category label."""
    parts = slug.split("-")
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        out.append(p[0].upper() + p[1:])
    return " ".join(out)
