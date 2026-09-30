"""Bootstrap TDEV Festival event + pass ticket types for production storefront checkout."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bootstrap import unlock_store_vault
from config import Config
from events import service as events_svc
from store import NotFoundError, Store
from store import orgs as orgs_repo
from store.store import new_ulid
from store.timeutil import time_to_text

DEFAULT_ORG_SLUG = "tdev"
DEFAULT_ORG_NAME = "T-Dev Community"
DEFAULT_EVENT_SLUG = "tdev-festival-2026"
DEFAULT_EVENT_TITLE = "TDEV Festival 2026"
DEFAULT_CURRENCY = "XOF"


def _ensure_org(store: Store, *, slug: str, name: str, currency: str) -> str:
    try:
        org = orgs_repo.get_org_by_slug(store, slug)
        return org.id
    except NotFoundError:
        pass
    org_id = new_ulid()
    now = datetime.now(timezone.utc)
    store.execute(
        """
        INSERT INTO orgs (id, name, slug, default_currency, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (org_id, name, slug, currency, time_to_text(now)),
    )
    return org_id


def seed_festival_storefront(
    store: Store,
    config: Config,
    *,
    org_slug: str = DEFAULT_ORG_SLUG,
    event_slug: str = DEFAULT_EVENT_SLUG,
    event_title: str = DEFAULT_EVENT_TITLE,
    currency: str = DEFAULT_CURRENCY,
) -> dict:
    """Create org, published festival event, and student/standard/vip pass types if missing."""
    unlock_store_vault(store, config)

    org_id = _ensure_org(store, slug=org_slug, name=DEFAULT_ORG_NAME, currency=currency)

    try:
        event = events_svc.get_by_slug_or_id(store, event_slug)
        event_id = event["id"]
        created = False
    except NotFoundError:
        now = datetime.now(timezone.utc)
        starts = now + timedelta(days=60)
        ends = starts + timedelta(days=2)
        event = events_svc.create(
            store,
            org_id,
            {
                "slug": event_slug,
                "title": event_title,
                "summary": "Festival tech TDEV 2026",
                "description": "Conférences, ateliers et soirée Nexus Night.",
                "venue_name": "Lieu principal du festival",
                "starts_at": starts.isoformat().replace("+00:00", "Z"),
                "ends_at": ends.isoformat().replace("+00:00", "Z"),
                "timezone": "Africa/Lome",
                "currency": currency,
                "category": "festival",
            },
        )
        event_id = event["id"]
        event = events_svc.publish(store, event_id)
        created = True

    events_svc.ensure_festival_pass_products(store, event_id)
    refreshed = events_svc.get(store, event_id)
    types = events_svc.list_storefront_products(store, event_id)
    return {
        "created_event": created,
        "org_id": org_id,
        "event": refreshed,
        "ticket_types": types,
    }
