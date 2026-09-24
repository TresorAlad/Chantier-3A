# Backend Python (billetterie)

API FastAPI pour la billetterie. Schéma SQL versionné :
`../backend/internal/store/migrations`.

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
| `CACKLE_DATABASE_URL` | Oui (sauf démo SQLite seul) | URL PostgreSQL (`postgresql://user:pass@host:5432/db?sslmode=require`) |
| `CACKLE_DB` | Recommandé | Fichier SQLite local (miroir + secrets session) |
| `CACKLE_KEY_PASSPHRASE` | Oui en prod | Passphrase du coffre de clés (signature billets) |
| `CACKLE_BASE_URL` | Recommandé | URL publique (`http://localhost:8080`) |

Exemple PostgreSQL (Neon, Supabase, etc.) :

```env
CACKLE_DATABASE_URL=postgresql://USER:PASSWORD@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
CACKLE_DB=./data/billetterie-local.db
CACKLE_KEY_PASSPHRASE=changez-moi-minimum-12-caracteres
CACKLE_BASE_URL=http://localhost:8080
CACKLE_ADDR=:8080
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
| `CACKLE_DATABASE_URL` défini | Migrations sur **PostgreSQL** (source de vérité) + sync schéma sur **SQLite** (`CACKLE_DB`) |
| Pas de `CACKLE_DATABASE_URL` | Migrations **SQLite uniquement** sur `CACKLE_DB` (défaut `./cackle.db`) |

Sortie attendue (PostgreSQL) :

```text
Using environment file: /.../backend-python/.env
PostgreSQL (primary): N migration(s) recorded.
  latest version: ...
SQLite (secondary): schema synced at ./data/billetterie-local.db
```

Fichiers SQL lus depuis :

- PostgreSQL : `../backend/internal/store/migrations/postgres/*.sql`
- SQLite : `../backend/internal/store/migrations/*.sql`

Relancer `billetterie-api migrate` est **idempotent** : seules les versions non appliquées sont exécutées.

### Dépannage migration

| Problème | Piste |
|----------|--------|
| `CACKLE_DATABASE_URL is not set` | Copier `.env.example` vers `.env` ou exporter la variable |
| Connexion PostgreSQL refusée | Vérifier URL, SSL (`sslmode=require`), pare-feu, IP autorisée |
| `migrations directory missing` | Vérifier que le dossier `../backend/internal/store/migrations` est présent |

---

## 4. Démarrer l'API

```bash
billetterie-api serve
```

Production / équipe : `CACKLE_DATABASE_URL` + `CACKLE_KEY_PASSPHRASE` requis.

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

Docker : `docker build -f Dockerfile.python -t billetterie-api .`

---

## 5. Structure du code

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

## 6. Périmètre API

| Domaine | État |
|---------|------|
| Auth, orgs, events, orders, tickets | Disponible |
| Paiements manual / stub / remote | Disponible |
| Scan offline, sync peer | Partiel |
| Payouts, pages event avancées | Stub ou 501 |

**Référence frontend (méthodes, paramètres, corps JSON, auth) :** [`docs/API-FRONTEND.md`](docs/API-FRONTEND.md).

Détails sync : `http_layer/routes/sync.py`.
