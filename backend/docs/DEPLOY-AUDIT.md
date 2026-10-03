# Audit deploiement backend (Render / Docker)

Checklist apres chaque changement du CLI ou des modules racine.

## 1. Packaging Python

| Fichier | Role |
|---------|------|
| `pyproject.toml` → `[tool.setuptools] py-modules` | Modules racine installes par `pip install .` |
| `Dockerfile` → ligne `COPY … *.py` | Fichiers copies avant `pip install` |
| `tests/test_packaging.py` | Verifie py-modules = COPY Dockerfile |

Commande locale :

```bash
cd backend
.venv/bin/pytest tests/test_packaging.py -q
docker build --target runtime -t billetterie-api .
```

Render utilise **uniquement** la cible `runtime` (pas `with-ui`).

## 2. Demarrage conteneur

```text
docker-entrypoint.sh serve
  → billetterie-api migrate   (prepare_production_database_url)
  → billetterie-api serve     (open_postgres, unlock key vault, uvicorn)
```

Erreurs frequentes :

| Log | Cause | Action |
|-----|-------|--------|
| `ModuleNotFoundError` | Module racine absent du Dockerfile / pyproject | Aligner COPY + py-modules |
| `AttributeError: … check` | API psycopg incompatible | Utiliser reconnect sur OperationalError (store.py) |
| `la cible PostgreSQL a change` | URL Neon modifiee sur Render | Remettre URL pooler Neon |
| Postgres Render refuse | URL `*.render.com` | Neon ou `CHANTIER3A_ALLOW_RENDER_POSTGRES=1` |

## 3. Variables Render (minimum)

Voir [`render.yaml`](../../render.yaml) et [`RENDER.md`](RENDER.md).

- `CHANTIER3A_DATABASE_URL` : pooler **Neon** (identique seed local)
- `CHANTIER3A_KEY_PASSPHRASE` : stable (ne pas changer en prod)
- `CHANTIER3A_DATA_DIR=/srv/data` + disque 1 Go monte
- `CHECKIN_SNAPSHOT_SIGNING_KEY` : `python -m checkin.signing` (une fois)

## 4. Validation post-deploy

```bash
curl -sS "https://<service>.onrender.com/healthz?db=1"
curl -sS "https://<service>.onrender.com/api/public/site-config"
curl -sS -X POST "https://<service>.onrender.com/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"…","password":"…"}'
```

Attendu : `database: up`, login `200` ou `401` (pas `500` / `503`).

## 5. Compte admin

```bash
export CHANTIER3A_BOOTSTRAP_STAFF=1
billetterie-api bootstrap-staff --email … --password '…' --name '…'
```

Ne jamais activer `CHANTIER3A_PUBLIC_SIGNUP=1` en prod sauf test ponctuel.
