# Chantier 3A — TDEV Festival

Branche **`main`** : API et billetterie web dans un même dépôt.

| Dossier | Rôle |
|---------|------|
| [`backend/`](./backend/) | API billetterie (FastAPI, PostgreSQL) |
| [`frontend-web/`](./frontend-web/) | Vitrine et billetterie (React, Vite) |

## Backend

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
billetterie-api migrate
billetterie-api serve
```

Documentation : [backend/README.md](./backend/README.md).

## Frontend

```bash
cd frontend-web
cp .env.example .env
npm install
npm run dev
```

Documentation : [frontend-web/README.md](./frontend-web/README.md).

## Tests

Procédure complète (tests automatiques, parcours de paiement FedaPay sandbox, e-mail, webhook) : [TESTING.md](./TESTING.md).

Historique des changements : [CHANGELOG.md](./CHANGELOG.md).

Admin organisateur (front) : [frontend-web/docs/ADMIN.md](./frontend-web/docs/ADMIN.md). Inscription reussie sans e-mail = verifier SMTP sur l'API (`email_configured` dans `/api/public/site-config`).

## Branches de travail

- `feat/Backend` — évolutions backend (`backend/` à la racine)
- `feat/frontend-web` — évolutions front (`frontend-web/` à la racine)

Dépôt : [github.com/TresorAlad/Chantier-3A](https://github.com/TresorAlad/Chantier-3A)
