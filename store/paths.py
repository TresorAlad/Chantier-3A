"""Resolve filesystem paths for media, database files, and SQL migrations."""

from pathlib import Path

_BACKEND_PYTHON_ROOT = Path(__file__).resolve().parents[1]
# Monorepo layout: .../<repo>/backend-python/store/paths.py -> repo root = parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]

_BUNDLED_MIGRATIONS = _BACKEND_PYTHON_ROOT / "migrations"
_MONOREPO_MIGRATIONS = REPO_ROOT / "backend" / "internal" / "store" / "migrations"

if _BUNDLED_MIGRATIONS.is_dir():
    MIGRATIONS_SQLITE = _BUNDLED_MIGRATIONS
else:
    MIGRATIONS_SQLITE = _MONOREPO_MIGRATIONS

MIGRATIONS_POSTGRES = MIGRATIONS_SQLITE / "postgres"

_bundled_frontend_dist = _BACKEND_PYTHON_ROOT / "frontend" / "dist"
FRONTEND_DIST = (
    _bundled_frontend_dist
    if _bundled_frontend_dist.is_dir()
    else REPO_ROOT / "frontend" / "dist"
)
