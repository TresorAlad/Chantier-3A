"""CLI entrypoint: migrate, serve (uvicorn), reset-password."""

from __future__ import annotations

import argparse
import logging
import os
import sys

import uvicorn

from config import load_config
from http_layer.app import create_app
from seed_festival import DEFAULT_EVENT_SLUG, seed_festival_storefront
from store import open_postgres
from store.db_identity import (
    database_target_label,
    prepare_production_database_url,
)
from store.migrate import migrate_store


def _setup_logging() -> None:
    """Internal: setup logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _require_database_url(cfg) -> str:
    """Internal: require database url."""
    url = (cfg.database_url or "").strip()
    if not url:
        print(
            "billetterie-api: CHANTIER3A_DATABASE_URL is required (PostgreSQL only).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return url


def cmd_migrate(args: argparse.Namespace) -> int:
    """Apply SQL migrations using CHANTIER3A_* from .env (see README)."""
    from config import load_env_file

    env_path = load_env_file()
    cfg = load_config(database_url=args.database_url or "")
    if env_path:
        print(f"Using environment file: {env_path}")
    production = os.getenv("CHANTIER3A_PYENV") == "production"
    url = prepare_production_database_url(
        _require_database_url(cfg),
        data_dir=cfg.data_dir,
        production=production,
    )
    print(f"billetterie-api: PostgreSQL cible={database_target_label(url)}", file=sys.stderr)
    try:
        versions = migrate_store(database_url=url)
    except Exception as err:
        print(f"billetterie-api migrate failed: {err}", file=sys.stderr)
        return 1
    print(f"Migrations (postgresql): {len(versions)} version(s) at {url}")
    if versions:
        print(f"  latest version: {versions[-1]}")
    return 0


def cmd_seed_festival(args: argparse.Namespace) -> int:
    """Create published TDEV festival event and pass ticket types (idempotent)."""
    cfg = load_config(database_url=args.database_url or "")
    url = _require_database_url(cfg)
    if not cfg.key_passphrase and not cfg.demo:
        print(
            "billetterie-api: CHANTIER3A_KEY_PASSPHRASE is required to sign tickets.",
            file=sys.stderr,
        )
        return 1
    store = open_postgres(url)
    try:
        result = seed_festival_storefront(
            store,
            cfg,
            event_slug=args.event_slug or DEFAULT_EVENT_SLUG,
        )
    except Exception as err:
        print(f"billetterie-api seed-festival failed: {err}", file=sys.stderr)
        return 1
    finally:
        store.close()

    ev = result["event"]
    action = "created" if result["created_event"] else "already present"
    print(f"Festival event ({action}): slug={ev['slug']} id={ev['id']} status={ev['status']}")
    print(f"Ticket types: {len(result['ticket_types'])}")
    for tt in result["ticket_types"]:
        tier = tt.get("pass_tier") or "-"
        print(f"  - {tt['name']} ({tier}) price_minor={tt['price_minor']} id={tt['id']}")
    return 0


def cmd_reset_password(args: argparse.Namespace) -> int:
    """Cmd reset password."""
    from auth import service as auth_svc

    cfg = load_config(database_url=args.database_url or "", demo=True)
    url = _require_database_url(cfg)
    store = open_postgres(url)
    try:
        token, expires = auth_svc.mint_password_reset_token(store, args.email)
    except auth_svc.InvalidEmail:
        print("billetterie-api: invalid email address", file=sys.stderr)
        return 1
    except auth_svc.NoSuchUser:
        print("billetterie-api: no account for that email", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"billetterie-api: {err}", file=sys.stderr)
        return 1
    else:
        print(token)
        print(f"expires: {expires.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        return 0
    finally:
        store.close()


def cmd_serve(args: argparse.Namespace) -> int:
    """Cmd serve."""
    demo = args.demo
    cfg = load_config(
        addr=args.addr or "",
        database_url=args.database_url or "",
        base_url=args.base_url or "",
        media_dir=args.media_dir or "",
        demo=demo,
    )
    os.makedirs(cfg.media_dir, mode=0o700, exist_ok=True)
    os.makedirs(cfg.data_dir, mode=0o700, exist_ok=True)

    production = os.getenv("CHANTIER3A_PYENV") == "production"
    url = prepare_production_database_url(
        _require_database_url(cfg),
        data_dir=cfg.data_dir,
        production=production,
    )
    print(f"billetterie-api: PostgreSQL cible={database_target_label(url)}", file=sys.stderr)
    if production and demo:
        print(
            "billetterie-api: CHANTIER3A_DEMO est interdit en production (desactivez CHANTIER3A_DEMO).",
            file=sys.stderr,
        )
        return 1
    if not cfg.key_passphrase and not demo:
        print(
            "billetterie-api: CHANTIER3A_KEY_PASSPHRASE is required when using PostgreSQL.",
            file=sys.stderr,
        )
        return 1
    store = open_postgres(url)

    app = create_app(store, cfg)
    host, port = _parse_addr(cfg.addr)
    uvicorn.run(app, host=host, port=port, log_level="info")
    store.close()
    return 0


def _parse_addr(addr: str) -> tuple[str, int]:
    """Internal: parse addr."""
    if addr.startswith(":"):
        return "0.0.0.0", int(addr[1:])
    if ":" in addr:
        host, port = addr.rsplit(":", 1)
        return host or "0.0.0.0", int(port)
    return "0.0.0.0", 8080


def main() -> None:
    """Main."""
    _setup_logging()
    parser = argparse.ArgumentParser(prog="billetterie-api", description="Ticketing API backend")
    sub = parser.add_subparsers(dest="command", required=True)

    p_migrate = sub.add_parser("migrate", help="Apply SQL migrations (PostgreSQL)")
    p_migrate.add_argument(
        "--database-url",
        default="",
        help="Override CHANTIER3A_DATABASE_URL",
    )

    p_serve = sub.add_parser("serve", help="Start the HTTP server")
    p_serve.add_argument("--addr", default="", help="Listen address (CHANTIER3A_ADDR)")
    p_serve.add_argument(
        "--database-url",
        default="",
        help="Override CHANTIER3A_DATABASE_URL",
    )
    p_serve.add_argument("--base-url", default="", help="Public base URL (CHANTIER3A_BASE_URL)")
    p_serve.add_argument("--media-dir", default="", help="Media upload directory")
    p_serve.add_argument(
        "--demo",
        action="store_true",
        help="Demo keyvault and stub payments (still requires PostgreSQL)",
    )

    p_seed = sub.add_parser(
        "seed-festival",
        help="Bootstrap published TDEV festival + pass tiers in PostgreSQL (production)",
    )
    p_seed.add_argument(
        "--database-url",
        default="",
        help="Override CHANTIER3A_DATABASE_URL",
    )
    p_seed.add_argument(
        "--event-slug",
        default="",
        help=f"Event slug (default {DEFAULT_EVENT_SLUG})",
    )

    p_reset = sub.add_parser("reset-password", help="Print a password reset token to stdout")
    p_reset.add_argument("email", help="Account email address")
    p_reset.add_argument(
        "--database-url",
        default="",
        help="Override CHANTIER3A_DATABASE_URL",
    )

    args = parser.parse_args()
    if args.command == "migrate":
        raise SystemExit(cmd_migrate(args))
    if args.command == "seed-festival":
        raise SystemExit(cmd_seed_festival(args))
    if args.command == "serve":
        raise SystemExit(cmd_serve(args))
    if args.command == "reset-password":
        raise SystemExit(cmd_reset_password(args))


if __name__ == "__main__":
    main()
