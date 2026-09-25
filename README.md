# Chantier 3A - Backend billetterie (Python)

API FastAPI pour la billetterie Chantier 3A. Schéma SQL versionné dans `migrations/`
(copie de `../backend/internal/store/migrations` ; repli monorepo si absent).

**Convention code :** docstrings et commentaires en anglais. Ce README est en français.

---

## Prérequis

| Outil | Version |
|-------|---------|
| Python | 3.11+ |
| PostgreSQL | 14+ (production / équipe) ou SQLite (`--demo` local) |

---

## 1. Installation

```bash
cd backend-python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## 2. Configuration (`.env`)

Créer le fichier d'environnement **avant** les migrations :

```bash
cp .env.example .env
```

Éditer `.env` au minimum :

| Variable | Obligatoire | Rôle |
|----------|-------------|------|
| `CHANTIER3A_DATABASE_URL` | Oui (sauf démo SQLite seul) | URL PostgreSQL (`postgresql://user:pass@host:5432/db?sslmode=require`) |
| `CHANTIER3A_DB` | Recommandé | Fichier SQLite local (miroir + secrets session) |
| `CHANTIER3A_KEY_PASSPHRASE` | Oui en prod | Passphrase du coffre de clés (signature billets) |
| `CHANTIER3A_BASE_URL` | Recommandé | URL publique (`http://localhost:8080`) |

Exemple PostgreSQL (Neon, Supabase, etc.) :

```env
CHANTIER3A_DATABASE_URL=postgresql://USER:PASSWORD@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
CHANTIER3A_DB=./data/billetterie-local.db
CHANTIER3A_KEY_PASSPHRASE=changez-moi-minimum-12-caracteres
CHANTIER3A_BASE_URL=http://localhost:8080
CHANTIER3A_ADDR=:8080
```

Le CLI charge automatiquement `backend-python/.env` (`python-dotenv`).

---

## 3. Migrations base de données

Appliquer le schéma **après** avoir rempli `.env` :

```bash
source .venv/bin/activate
billetterie-api migrate
```

### Comportement

| Configuration | Action |
|---------------|--------|
| `CHANTIER3A_DATABASE_URL` défini | Migrations sur **PostgreSQL** (source de vérité) + sync schéma sur **SQLite** (`CHANTIER3A_DB`) |
| Pas de `CHANTIER3A_DATABASE_URL` | Migrations **SQLite uniquement** sur `CHANTIER3A_DB` (défaut `./billetterie.db`) |

Sortie attendue (PostgreSQL) :

```text
Using environment file: /.../backend-python/.env
PostgreSQL (primary): N migration(s) recorded.
  latest version: ...
SQLite (secondary): schema synced at ./data/billetterie-local.db
```

Fichiers SQL lus depuis :

- PostgreSQL : `migrations/postgres/*.sql`
- SQLite : `migrations/*.sql`

Relancer `billetterie-api migrate` est **idempotent** : seules les versions non appliquées sont exécutées.

### Dépannage migration

| Problème | Piste |
|----------|--------|
| `CHANTIER3A_DATABASE_URL is not set` | Copier `.env.example` vers `.env` ou exporter la variable |
| Connexion PostgreSQL refusée | Vérifier URL, SSL (`sslmode=require`), pare-feu, IP autorisée |
| `migrations directory missing` | Vérifier que le dossier `migrations/` est présent dans le dépôt |

---

## 4. Démarrer l'API

```bash
billetterie-api serve
```

Production / équipe : `CHANTIER3A_DATABASE_URL` + `CHANTIER3A_KEY_PASSPHRASE` requis.

Démo locale sans PostgreSQL :

```bash
billetterie-api migrate    # SQLite seul si pas de DATABASE_URL
billetterie-api serve --demo
```

Autres commandes :

```bash
billetterie-api reset-password user@example.com
```

Racine du dépôt : `make run-python` (équivalent `serve --demo`).

## 5. Docker

Un seul `docker-compose.yml`, piloté par le fichier **`.env`** (mêmes variables que le CLI).

```bash
cp .env.example .env
# Editer CHANTIER3A_KEY_PASSPHRASE, CHANTIER3A_DATABASE_URL, etc.
docker compose up --build
```

Par défaut (`.env.example`) : profil **`local-db`** (`COMPOSE_PROFILES=local-db`) + Postgres dans Compose + `CHANTIER3A_DATABASE_URL=...@db:5432/...`. Migrations au démarrage du conteneur.

| Besoin | `.env` |
|--------|--------|
| Postgres fourni par Compose | `COMPOSE_PROFILES=local-db` et URL avec host `db` |
| Postgres externe (Neon, etc.) | Vider `COMPOSE_PROFILES`, URL distante dans `CHANTIER3A_DATABASE_URL` |
| Démo SQLite dans Docker | `CHANTIER3A_DEMO=1`, `CHANTIER3A_DATABASE_URL` vide, sans `local-db` |
| Image avec UI React (monorepo) | `CHANTIER3A_DOCKER_BUILD_CONTEXT=..`, `CHANTIER3A_DOCKERFILE=backend-python/Dockerfile`, `CHANTIER3A_DOCKER_TARGET=with-ui` |

Build manuel : `docker build -t billetterie-api .`

---

## 6. Structure du code

```text
backend-python/
  auth/
  events/
  http_layer/       # FastAPI (routes, middleware)
  money/
  notify/
  orders/
  payments/
  scan/
  store/            # SQL, migrations (migrate.py)
  tickets/
  config.py         # charge .env
  cli.py            # migrate | serve | reset-password
  tests/
```

Architecture chantier 3A : `../docs/BILLETTERIE-3A-ARCHITECTURE.md`.

---

## 7. Périmètre API

| Domaine | État |
|---------|------|
| Auth, orgs, events, orders, tickets | Disponible |
| Paiements manual / stub / remote | Disponible |
| Scan offline, sync peer | Partiel |
| Payouts, pages event avancées | Stub ou 501 |

**Référence frontend (méthodes, paramètres, corps JSON, auth) :** [`docs/API-FRONTEND.md`](docs/API-FRONTEND.md).

Détails sync : `http_layer/routes/sync.py`.
