"""Verrouillage cible PostgreSQL en production."""

import pytest

from store.db_identity import (
    assert_production_database_url,
    database_target_label,
    enforce_stable_database_target,
    normalize_database_url,
    warn_if_likely_empty_render_postgres,
)


def test_database_target_label_hides_secrets():
    url = "postgresql://user:secret@ep-cool.neon.tech/neondb?sslmode=require"
    assert database_target_label(url) == "ep-cool.neon.tech/neondb"


def test_enforce_blocks_url_change_in_production(tmp_path):
    data = str(tmp_path)
    url_a = "postgresql://u:p@ep-a.neon.tech/neondb"
    url_b = "postgresql://u:p@ep-b.neon.tech/neondb"
    enforce_stable_database_target(data, url_a, production=True)
    with pytest.raises(SystemExit):
        enforce_stable_database_target(data, url_b, production=True)


def test_enforce_allows_override_env(tmp_path, monkeypatch):
    data = str(tmp_path)
    url_a = "postgresql://u:p@ep-a.neon.tech/neondb"
    url_b = "postgresql://u:p@ep-b.neon.tech/neondb"
    enforce_stable_database_target(data, url_a, production=True)
    monkeypatch.setenv("CHANTIER3A_ALLOW_DATABASE_URL_CHANGE", "1")
    enforce_stable_database_target(data, url_b, production=True)


def test_normalize_adds_sslmode_for_neon():
    url = "postgresql://u:p@ep-cool.neon.tech/neondb"
    assert normalize_database_url(url) == f"{url}?sslmode=require"
    with_ssl = f"{url}?sslmode=disable"
    assert normalize_database_url(with_ssl) == with_ssl


def test_assert_blocks_render_postgres_in_production():
    url = "postgresql://u:p@dpg-xxxx-a.frankfurt-postgres.render.com/chantier3a"
    with pytest.raises(SystemExit):
        assert_production_database_url(url, production=True)


def test_assert_allows_render_postgres_with_opt_in(monkeypatch):
    monkeypatch.setenv("CHANTIER3A_ALLOW_RENDER_POSTGRES", "1")
    url = "postgresql://u:p@dpg-xxxx-a.frankfurt-postgres.render.com/chantier3a"
    assert_production_database_url(url, production=True)


def test_warn_render_postgres():
    msg = warn_if_likely_empty_render_postgres(
        "postgresql://u:p@dpg-xxxx-a.frankfurt-postgres.render.com/chantier3a",
    )
    assert msg is not None
    assert "Neon" in msg
