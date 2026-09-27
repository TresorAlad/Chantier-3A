# Chantier 3A - Backend billetterie (Python)

API FastAPI pour la billetterie Chantier 3A. Schéma SQL versionné dans `migrations/` (PostgreSQL).

**Convention code :** docstrings et commentaires en anglais. Ce README est en français.

---

## Prérequis

| Outil | Version |
|-------|---------|
| Python | 3.11+ |
| PostgreSQL | 14+ (`CHANTIER3A_DATABASE_URL` obligatoire) |

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
| `CHANTIER3A_DATABASE_URL` | Oui | URL PostgreSQL (`postgresql://user:pass@host:5432/db?sslmode=require`) |
| `CHANTIER3A_DATA_DIR` | Recommandé | Répertoire local (session, médias ; défaut `./data`) |
| `CHANTIER3A_KEY_PASSPHRASE` | Oui en prod | Passphrase du coffre de clés (signature billets) |
| `CHANTIER3A_BASE_URL` | Recommandé | URL publique (`http://localhost:8080`) |

Exemple PostgreSQL (Neon, Supabase, etc.) :

```env
CHANTIER3A_DATABASE_URL=postgresql://USER:PASSWORD@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
CHANTIER3A_DATA_DIR=./data
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

### Comportement (une commande, une base)

Le CLI lit `.env` et migre **un seul** moteur :

Migrations : **PostgreSQL uniquement**, via `CHANTIER3A_DATABASE_URL` (Neon, Compose `db`, etc.).

Sortie type :

```text
Using environment file: /.../backend-python/.env
Migrations (postgresql): 13 version(s) at postgresql://...
  latest version: 13
```

Les scripts SQL sont dans `migrations/` (numérotés `0001_`, …, jusqu’à **0013**). Les versions déjà appliquées sont suivies dans la table `schema_migrations`.

Relancer `billetterie-api migrate` est **idempotent** : seules les versions non encore appliquées sont exécutées.

### Dépannage migration

| Problème | Piste |
|----------|--------|
| `CHANTIER3A_DATABASE_URL is required` | Copier `.env.example` vers `.env` ou exporter la variable |
| Connexion PostgreSQL refusée | Vérifier URL, SSL (`sslmode=require`), pare-feu, IP autorisée |
| `migrations directory missing` | Vérifier que le dossier `migrations/` est présent dans le dépôt |

---

## 4. Démarrer l'API

```bash
billetterie-api serve
```

PostgreSQL : renseigner `CHANTIER3A_DATABASE_URL` + `CHANTIER3A_KEY_PASSPHRASE`.

Option `--demo` : coffre de clés et paiements factices (PostgreSQL toujours requis).

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
| Postgres dans Compose | `COMPOSE_PROFILES=local-db`, `CHANTIER3A_DATABASE_URL=...@db:5432/...` |
| Postgres externe | URL distante dans `CHANTIER3A_DATABASE_URL` (Compose `db` optionnel) |
| Image avec UI React (monorepo) | `CHANTIER3A_DOCKER_BUILD_CONTEXT=..`, `CHANTIER3A_DOCKERFILE=backend-python/Dockerfile`, `CHANTIER3A_DOCKER_TARGET=with-ui` |

Au démarrage, le conteneur exécute `billetterie-api migrate` puis `serve` (désactivable avec `CHANTIER3A_SKIP_MIGRATE=1`).

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

## 7. Périmètre API (V1)

| Domaine | État |
|---------|------|
| Auth, orgs, events, orders, tickets | Disponible |
| Paiements manual / stub / remote | Disponible |
| Scan porte (`POST /api/scan`) | Disponible (en ligne) |
| Offline, bundle, sync, peers | **Retiré** |
| Payouts, pages event avancées | Stub ou 501 |

Backend **en ligne uniquement** : [`docs/V1-SCOPE.md`](docs/V1-SCOPE.md).

**Référence frontend :** [`docs/API-FRONTEND.md`](docs/API-FRONTEND.md).
