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
git clone https://github.com/TresorAlad/Chantier-3A.git
cd Chantier-3A
git checkout feat/Backend
cd backend
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
| `CHECKIN_SNAPSHOT_SIGNING_KEY` | Oui avec le mobile | Graine Ed25519 dédiée à la signature des données hors ligne (`python -m checkin.signing`) |

Variables optionnelles :

| Variable | Défaut | Rôle |
|----------|--------|------|
| `CHANTIER3A_ADDR` | `:8080` | Adresse d'écoute de `serve` |
| `CHANTIER3A_PUBLIC_SIGNUP` | off (on avec `--demo`) | Autorise `POST /api/auth/signup` |
| `CHANTIER3A_PAYMENT_PROVIDERS` | `manual` | Providers de paiement autorisés (`manual,fedapay`) |
| `CHANTIER3A_FEDAPAY_SECRET_KEY` | vide | Clé secrète FedaPay (`sk_sandbox_…` / `sk_live_…`). Active le provider `fedapay` si renseignée |
| `CHANTIER3A_FEDAPAY_WEBHOOK_SECRET` | vide | Secret du webhook FedaPay (`wh_…`). Vide : tout webhook reçu est refusé (400) |
| `CHANTIER3A_FEDAPAY_ENV` | `sandbox` | `sandbox` ou `live` |
| `CHANTIER3A_SMTP_HOST`, `_PORT` (587), `_USER`, `_PASSWORD`, `_FROM` | vide | E-mail de confirmation avec billet PDF. Sans `HOST` et `FROM`, aucun e-mail n'est envoyé (message dans les logs) |
| `CHANTIER3A_PAYMENT_SERVICE_URL`, `_API_KEY`, `CHANTIER3A_PAYMENT_WEBHOOK_SECRET`, `CHANTIER3A_PAYMENT_PROVIDER_NAME` | vide | Provider distant (microservice) : voir [`docs/PAYMENT-SERVICE.md`](docs/PAYMENT-SERVICE.md) |

**`CHANTIER3A_BASE_URL` joue trois rôles** : origine autorisée par le CORS (une seule, celle du navigateur), URL de retour envoyée à FedaPay, et base du lien « Télécharger mon billet » de l'e-mail (`{BASE_URL}/api/orders/<id>/guest/ticket.pdf`). Elle doit donc être l'adresse publique du site, avec `/api` routé vers ce backend (reverse proxy). En dev, laissez le front passer par le proxy Vite (`VITE_DEV_API_PROXY`) plutôt que d'appeler l'API en cross-origin.

Paiement FedaPay : voir [`../TESTING.md`](../TESTING.md) (procédure) et [`docs/API-FRONTEND.md`](docs/API-FRONTEND.md) (contrat) ; mise en production : [`docs/PRODUCTION-FEDAPAY.md`](docs/PRODUCTION-FEDAPAY.md).

Exemple PostgreSQL (Neon, Supabase, etc.) :

```env
CHANTIER3A_DATABASE_URL=postgresql://USER:PASSWORD@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
CHANTIER3A_DATA_DIR=./data
CHANTIER3A_KEY_PASSPHRASE=changez-moi-minimum-12-caracteres
CHANTIER3A_BASE_URL=http://localhost:8080
CHANTIER3A_ADDR=:8080
```

Le CLI charge automatiquement `backend/.env` (`python-dotenv`).

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

Les scripts SQL sont dans `migrations/` (numérotés `0001_`, …, jusqu’à **0022**). Les versions déjà appliquées sont suivies dans la table `schema_migrations`.

Relancer `billetterie-api migrate` est **idempotent** : seules les versions non encore appliquées sont exécutées.

### Dépannage migration

| Problème | Piste |
|----------|--------|
| `CHANTIER3A_DATABASE_URL is required` | Copier `.env.example` vers `.env` ou exporter la variable |
| Connexion PostgreSQL refusée | Vérifier URL, SSL (`sslmode=require`), pare-feu, IP autorisée |
| Render : billetterie vide ou deploy en echec | URL Neon identique au seed ; voir [`docs/RENDER.md`](docs/RENDER.md). Postgres Render refuse par defaut (`CHANTIER3A_ALLOW_RENDER_POSTGRES=1` si base Render seedee) |
| `la cible PostgreSQL a change` | Remettre l URL Neon d origine ou `CHANTIER3A_ALLOW_DATABASE_URL_CHANGE=1` une fois |
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

## 5b. Render (hébergement cloud)

Blueprint à la racine du monorepo : [`../render.yaml`](../render.yaml). Procédure détaillée : [`docs/RENDER.md`](docs/RENDER.md).

En bref : Web Service Docker (`backend/`), Postgres Render, disque sur `/srv/data`, migrations au démarrage. La variable **`PORT`** (injectée par Render) est prise en charge automatiquement ; définir `CHANTIER3A_PYENV=production` pour les cookies de session en HTTPS.

---

## 6. Structure du code

```text
backend-python/
  auth/
  events/
  http_layer/       # FastAPI (routes, middleware)
  money/
  notify/           # e-mail + billet PDF/PNG (assets/ : polices, logo)
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
| Paiements manual / free / stub / remote / **fedapay** (Checkout.js, XOF) | Disponible |
| Scan sectorisé (`POST /api/scan`) | Disponible (entrée, repas, goodies, after) |
| Synchronisation mobile (`POST /api/scan/sync`) | Disponible, lots idempotents jusqu'à 500 opérations |
| Conflits d'admission | Disponible par événement et type de contrôle |
| Bundle de droits offline (`GET /api/events/{event_id}/scan-bundle`) | Disponible avec clés, capacités et droits explicites |
| Payouts, pages event avancées | Stub ou 501 |

Le scan en ligne et la remontée différée des opérations offline sont pris en charge.

**Référence frontend :** [`docs/API-FRONTEND.md`](docs/API-FRONTEND.md).

## Tests

```bash
python -m pytest tests -q
```

Par défaut chaque test tourne sur une base **SQLite jetable** (`tests/sqlite_store.py` applique les vraies migrations en traduisant les quelques constructions PostgreSQL). L'application, elle, reste PostgreSQL uniquement.

Pour tester sur PostgreSQL, définir `TEST_DATABASE_URL` vers une base dont le nom finit par `_test` (la suite vide toutes les tables ; toute autre base est refusée). Les variables `CHANTIER3A_*` de `backend/.env` ne sont pas chargées pendant les tests.
