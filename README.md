# Branche `feat/Backend` — Chantier 3A

L'API billetterie (FastAPI, PostgreSQL) se trouve dans le dossier **`backend/`**.

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
billetterie-api migrate
billetterie-api serve
```

Documentation détaillée : [backend/README.md](./backend/README.md).
