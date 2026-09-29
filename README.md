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
| `CHANTIER3A_SESSION_SECRET` | Recommandé | Secret pour signer les cookies de session et les tokens internes |
| `CHANTIER3A_KEY_PASSPHRASE` | Oui en prod | Passphrase du coffre de clés (signature billets) |
| `CHANTIER3A_BASE_URL` | Recommandé | URL publique (`http://localhost:8080`) |
| `CHANTIER3A_SECRET_KEY` | Oui pour JWT | Clé de signature des JWT access tokens |
| `CHANTIER3A_ALGORITHM` | Oui pour JWT | Algorithme JWT (ex. `HS256`) |
| `CHANTIER3A_ACCESS_TOKEN_EXPIRE_MINUTES` | Oui pour JWT | Durée de vie de l’access token |
| `CHANTIER3A_GOOGLE_CLIENT_ID` | Requis pour OAuth Google | Client ID OAuth Google |
| `CHANTIER3A_GOOGLE_CLIENT_SECRET` | Requis pour OAuth Google | Secret OAuth Google |
| `CHANTIER3A_OAUTH_STATE_SECRET` | Requis pour OAuth Google | Secret de validation de l’état OAuth |
| `CHANTIER3A_GOOGLE_REDIRECT_URI` | Recommandé | URL de callback Google |

Exemple PostgreSQL (Neon, Supabase, etc.) :

```env
CHANTIER3A_DATABASE_URL=postgresql://USER:PASSWORD@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
CHANTIER3A_DATA_DIR=./data
CHANTIER3A_KEY_PASSPHRASE=changez-moi-minimum-12-caracteres
CHANTIER3A_BASE_URL=http://localhost:8080
CHANTIER3A_ADDR=:8080
CHANTIER3A_SECRET_KEY=changez-moi-avec-une-clef-très-longue-et-aléatoire
CHANTIER3A_ALGORITHM=HS256
CHANTIER3A_ACCESS_TOKEN_EXPIRE_MINUTES=60
CHANTIER3A_GOOGLE_CLIENT_ID=your-google-client-id
CHANTIER3A_GOOGLE_CLIENT_SECRET=your-google-client-secret
CHANTIER3A_OAUTH_STATE_SECRET=changez-moi-aussi
CHANTIER3A_GOOGLE_REDIRECT_URI=http://localhost:8080/api/v1/auth/google/callback
```

Le CLI charge automatiquement `backend-python/.env` (`python-dotenv`).

---

## 3. Authentification JWT, refresh token et OAuth

Le backend implémente désormais un flux d’authentification basé sur des cookies HTTP sécurisés et des JWT.

### Flux actuel

- L’utilisateur s’inscrit ou se connecte via l’API locale ou via Google OAuth.
- Le backend émet un `access token` court terme et un `refresh token` long terme.
- Les tokens sont stockés dans des cookies HTTP sécurisés :
  - `jwt_token` pour l’access token
  - `refresh_token` pour le refresh token
- Les appels API protégés vérifient le JWT via le middleware/dep d’authentification.
- Les comptes désactivés (`disabled = true`) sont rejetés systématiquement, même si le token est valide.

### Sécurité appliquée

- `access token` : durée courte, signé par `CHANTIER3A_SECRET_KEY` avec `CHANTIER3A_ALGORITHM`.
- `refresh token` : token opaque stocké côté base de données et lié à l’utilisateur.
- Rotation du refresh token : un refresh validé génère un nouveau couple access + refresh.
- Revoke côté logout : le refresh token est invalidé et les cookies sont supprimés.
- OAuth Google : le callback produit le même type d’authentification que le login local, avec flux de cookies cohérent.

### Endpoints d’authentification

Les routes principales sont les suivantes :

- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/google`
- `GET /api/v1/auth/google/callback`

Le refresh endpoint renvoie un nouveau JWT et remplace le refresh token précédent. Le logout invalide le refresh stocké et supprime les cookies de session.

### Points de configuration

Pour un environnement sécurisé, les variables minimales suivantes doivent être définies :

```env
CHANTIER3A_SECRET_KEY=une-clef-de-32-plus-octets
CHANTIER3A_ALGORITHM=HS256
CHANTIER3A_ACCESS_TOKEN_EXPIRE_MINUTES=60
CHANTIER3A_SESSION_SECRET=une-clef-secrète-pour-les-cookies
```

Pour le OAuth Google :

```env
CHANTIER3A_GOOGLE_CLIENT_ID=...
CHANTIER3A_GOOGLE_CLIENT_SECRET=...
CHANTIER3A_OAUTH_STATE_SECRET=...
CHANTIER3A_GOOGLE_REDIRECT_URI=http://localhost:8080/api/v1/auth/google/callback
```

---

## 4. Migrations base de données

---

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
Migrations (postgresql): 15 version(s) at postgresql://...
  latest version: 15
```

Les scripts SQL sont dans `migrations/` (numérotés `0001_`, …, jusqu’à **0015**). Les versions déjà appliquées sont suivies dans la table `schema_migrations`.

Relancer `billetterie-api migrate` est **idempotent** : seules les versions non encore appliquées sont exécutées.

### Dépannage migration

| Problème | Piste |
|----------|--------|
| `CHANTIER3A_DATABASE_URL is required` | Copier `.env.example` vers `.env` ou exporter la variable |
| Connexion PostgreSQL refusée | Vérifier URL, SSL (`sslmode=require`), pare-feu, IP autorisée |
| `migrations directory missing` | Vérifier que le dossier `migrations/` est présent dans le dépôt |
| Migration annoncée mais aucune table visible | Vérifier que l’outil SQL utilise le même serveur et la même base que `CHANTIER3A_DATABASE_URL`, puis actualiser la liste des tables. Dans PostgreSQL, contrôler `SELECT current_database(), current_schema();` et la table `public.schema_migrations`. |

---

## 5. Démarrer l'API

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

## 6. Docker

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

## 7. Structure du code

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

## 8. Périmètre API (V1)

| Domaine | État |
|---------|------|
| Auth, orgs, events, orders, tickets | Disponible |
| Paiements manual / stub / remote | Disponible |
| Scan porte (`POST /api/scan`) | Disponible (en ligne) |
| Offline, bundle, sync, peers | **Retiré** |
| Payouts, pages event avancées | Stub ou 501 |

Backend **en ligne uniquement** : [`docs/V1-SCOPE.md`](docs/V1-SCOPE.md).

**Référence frontend :** [`docs/API-FRONTEND.md`](docs/API-FRONTEND.md).
