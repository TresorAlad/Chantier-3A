"""Health, version, and host capability metadata routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Query, Request

from config import Config
from http_layer.deps import AppState, get_app_state
from http_layer.errors import json_error
from store import orgs

root_router = APIRouter(tags=["meta"])
api_router = APIRouter(tags=["meta"])


@root_router.get("/healthz")
def healthz(request: Request, db: bool | None = Query(None)) -> dict:
    """Healthz. En production, vérifie PostgreSQL par défaut (Render health check)."""
    check_db = db if db is not None else os.getenv("CHANTIER3A_PYENV") == "production"
    if not check_db:
        return {"status": "ok"}
    store = request.app.state.store
    try:
        row = store.fetchone("SELECT 1 AS ok", ())
        if row is None or (row.get("ok") if hasattr(row, "get") else row[0]) != 1:
            raise RuntimeError("unexpected health query result")
    except Exception:
        return json_error(503, "database_unavailable", "PostgreSQL unreachable or misconfigured")
    cfg: Config = request.app.state.config
    out: dict = {"status": "ok", "database": "up"}
    if check_db and getattr(cfg, "database_url", ""):
        from store.db_identity import database_target_label

        out["database_target"] = database_target_label(cfg.database_url)
    return out


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
        "contact_email": (cfg.contact_to or cfg.smtp_from or "").strip(),
        "contact_form_enabled": bool(cfg.smtp_host and cfg.smtp_from and (cfg.contact_to or cfg.smtp_from)),
        "public_signup": cfg.public_signup,
        "visitor_checkout_without_account": True,
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


@api_router.get("/pass-tiers")
def pass_tiers() -> dict:
    """Festival pass tiers currently offered on the storefront."""
    from events.passes import pass_tier_catalog

    return {"pass_tiers": pass_tier_catalog()}
