"""Health, version, and host capability metadata routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from config import Config
from http_layer.deps import AppState, get_app_state
from store import orgs

root_router = APIRouter(tags=["meta"])
api_router = APIRouter(tags=["meta"])


@root_router.get("/healthz")
def healthz() -> dict:
    """Healthz."""
    return {"status": "ok"}


@api_router.get("/public/site-config")
def site_config(state: AppState = Depends(get_app_state)) -> dict:
    """Site config."""
    cfg: Config = state.config
    org_create_disabled = False
    if cfg.community_mode:
        try:
            org_create_disabled = orgs.count_orgs(state.store) >= 1
        except Exception:
            org_create_disabled = False
    return {
        "community_mode": cfg.community_mode,
        "host_scope": cfg.host_scope,
        "host_name": cfg.host_name,
        "host_org": cfg.host_org,
        "org_create_disabled": org_create_disabled,
        "email_configured": bool(cfg.smtp_from and cfg.smtp_host),
    }


@api_router.get("/categories")
def categories(state: AppState = Depends(get_app_state)) -> dict:
    """Categories."""
    from events import service as events_svc
    from store import events_repo

    counts = events_repo.list_category_counts(state.store)
    out = [
        {"slug": c.slug, "label": events_svc.category_label(c.slug), "count": c.count}
        for c in counts
    ]
    return {"categories": out}


@api_router.get("/currencies")
def currencies() -> dict:
    """Currencies."""
    from money import currency as money

    return {"currencies": money.list_currencies()}
