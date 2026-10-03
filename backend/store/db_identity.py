"""Verrouillage de la cible PostgreSQL en production (disque persistant Render)."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from urllib.parse import urlparse


def database_target_label(database_url: str) -> str:
    """Hôte et nom de base uniquement (sans identifiants), pour logs et health check."""
    raw = database_url.strip().replace("postgresql://", "postgres://", 1)
    parsed = urlparse(raw)
    host = parsed.hostname or "?"
    db = (parsed.path or "").lstrip("/").split("?")[0] or "?"
    return f"{host}/{db}"


def _identity_path(data_dir: str) -> Path:
    return Path(data_dir).resolve() / ".chantier3a_db_identity"


def enforce_stable_database_target(
    data_dir: str,
    database_url: str,
    *,
    production: bool,
) -> None:
    """
    En production, enregistre host/db sur le disque persistant au premier démarrage.
    Si CHANTIER3A_DATABASE_URL change ensuite (ex. lien Postgres Render au lieu de Neon),
    le serveur refuse de démarrer au lieu d'utiliser silencieusement une base vide.
    """
    if not production:
        return
    if os.getenv("CHANTIER3A_ALLOW_DATABASE_URL_CHANGE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return

    current = database_target_label(database_url)
    path = _identity_path(data_dir)

    if path.is_file():
        previous = path.read_text(encoding="utf-8").strip()
        if previous and previous != current:
            raise SystemExit(
                "billetterie-api: la cible PostgreSQL a change "
                f"({previous} -> {current}). "
                "Les donnees semblent effacees car l'API pointe vers une autre base. "
                "Sur Render, remettez la meme URL Neon dans CHANTIER3A_DATABASE_URL "
                "(identique au seed local), puis redeployez. "
                "Changement volontaire de base : definir CHANTIER3A_ALLOW_DATABASE_URL_CHANGE=1 "
                f"une fois, ou supprimer {path} sur le disque persistant."
            )
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(current + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def normalize_database_url(database_url: str) -> str:
    """Ajoute sslmode=require pour Neon si absent (Render exige TLS)."""
    url = database_url.strip()
    if not url:
        return url
    host_segment = url.split("@", 1)[-1].lower() if "@" in url else url.lower()
    if "neon.tech" in host_segment and "sslmode=" not in url.lower():
        return f"{url}&sslmode=require" if "?" in url else f"{url}?sslmode=require"
    return url


def prepare_production_database_url(
    database_url: str,
    *,
    data_dir: str,
    production: bool,
) -> str:
    """
    Normalise l URL, refuse le Postgres Render vide par defaut, verrouille host/db sur disque.
    A appeler avant migrate et serve en production.
    """
    url = normalize_database_url(database_url)
    assert_production_database_url(url, production=production)
    enforce_stable_database_target(data_dir, url, production=production)
    return url


def assert_production_database_url(database_url: str, *, production: bool) -> None:
    """En production, refuse le Postgres Render sauf opt-in explicite."""
    if not production:
        return
    hint = warn_if_likely_empty_render_postgres(database_url)
    if not hint:
        return
    allow = os.getenv("CHANTIER3A_ALLOW_RENDER_POSTGRES", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if allow:
        print(f"billetterie-api: {hint}", file=sys.stderr)
        return
    raise SystemExit(
        f"{hint} "
        "Demarrage refuse en production. Collez l URL Neon (pooler) dans CHANTIER3A_DATABASE_URL. "
        "Base Render dediee et seedee : CHANTIER3A_ALLOW_RENDER_POSTGRES=1."
    )


def warn_if_likely_empty_render_postgres(database_url: str) -> str | None:
    """Message d'avertissement si l'URL ressemble au Postgres Render (souvent vide)."""
    label = database_target_label(database_url).lower()
    host = label.split("/", 1)[0]
    if "neon" in host:
        return None
    if "render.com" in host or host.endswith(".internal"):
        return (
            "billetterie-api: CHANTIER3A_DATABASE_URL ressemble au Postgres Render "
            f"({host}). Pour TDEV Festival, utilisez l'URL Neon (meme base que seed-festival)."
        )
    return None
