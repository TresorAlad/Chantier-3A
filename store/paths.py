"""Resolve filesystem paths for media and database files."""

from pathlib import Path

# backend-python/store/paths.py -> monorepo root = parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_SQLITE = REPO_ROOT / "backend" / "internal" / "store" / "migrations"
MIGRATIONS_POSTGRES = MIGRATIONS_SQLITE / "postgres"
