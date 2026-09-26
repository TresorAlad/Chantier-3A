"""Resolve filesystem paths for media and SQL migrations."""

from pathlib import Path

_BACKEND_PYTHON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]

_BUNDLED_MIGRATIONS = _BACKEND_PYTHON_ROOT / "migrations"
_MONOREPO_MIGRATIONS = REPO_ROOT / "backend" / "internal" / "store" / "migrations"

MIGRATIONS_DIR = (
    _BUNDLED_MIGRATIONS if _BUNDLED_MIGRATIONS.is_dir() else _MONOREPO_MIGRATIONS
)

_bundled_frontend_dist = _BACKEND_PYTHON_ROOT / "frontend" / "dist"
FRONTEND_DIST = (
    _bundled_frontend_dist
    if _bundled_frontend_dist.is_dir()
    else REPO_ROOT / "frontend" / "dist"
)
