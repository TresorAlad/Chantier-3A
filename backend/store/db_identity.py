"""Verrouillage de la cible PostgreSQL en production (disque persistant Render)."""

from __future__ import annotations

import os
from pathlib import Path
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
