"""Resolve filesystem paths for media and SQL migrations."""

from pathlib import Path

# ``store`` package lives at ``<backend>/store`` (dev) or ``site-packages/store`` (install).
_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_BUNDLED_MIGRATIONS = _BACKEND_ROOT / "migrations"
# Legacy monorepo layout (pre-backend-python rename).
_LEGACY_MIGRATIONS = (
    _BACKEND_ROOT.parent / "backend" / "internal" / "store" / "migrations"
)


def _pick_migrations_dir() -> Path:
    for candidate in (_BUNDLED_MIGRATIONS, _LEGACY_MIGRATIONS):
        if candidate.is_dir() and any(candidate.glob("*.sql")):
            return candidate
    raise FileNotFoundError(
        f"migrations directory missing: tried {_BUNDLED_MIGRATIONS} and {_LEGACY_MIGRATIONS}"
    )


MIGRATIONS_DIR = _pick_migrations_dir()

REPO_ROOT = Path(__file__).resolve().parents[2]

_bundled_frontend_dist = _BACKEND_ROOT / "frontend" / "dist"
FRONTEND_DIST = (
    _bundled_frontend_dist
    if _bundled_frontend_dist.is_dir()
    else REPO_ROOT / "frontend" / "dist"
)
