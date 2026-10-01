# Hébergement Render (backend API)

Guide pour déployer le backend FastAPI (`backend/`) sur [Render](https://render.com) avec PostgreSQL et stockage persistant pour les médias et le coffre de clés.

## Option recommandée : projet Render (Production)

Dans le dashboard : **My Workspace** > votre projet (ex. `billeterie`) > **Production** > **New** (ou **Add service**). Créer les ressources **dans cet ordre**.

### 1. Postgres

Choisir la carte **Postgres**.

| Champ | Valeur |
|-------|--------|
| Name | ex. `billeterie-db` |
| Database / User | laisser ou `chantier3a` |
| Region | même région que l'API (ex. Frankfurt) |
| Plan | selon budget |

Une fois créé : onglet **Connect** > copier l'**Internal Database URL** (pour le Web Service sur Render, pas l'URL externe).

### 2. Web Service (API)

Retourner au projet > **New** > **Web Services**.

| Champ | Valeur |
|-------|--------|
| Source | repo GitHub `Chantier-3A`, branche `main` |
| Language | **Docker** |
| Root Directory | `backend` |
| Dockerfile | `Dockerfile` (défaut) |
| Name | ex. `billeterie-api` |
| Health Check Path | `/healthz?db=1` (ou `/healthz` en prod : la base est testée automatiquement) |
| Instance type | Starter ou plus |

**Disque persistant** (Settings ou à la création si proposé) :

- Mount path : `/srv/data`
- Taille : 1 Go minimum

**Environment** (minimum) :

```env
CHANTIER3A_PYENV=production
CHANTIER3A_DATABASE_URL=<PostgreSQL : URL interne Render **ou** pooler Neon identique au seed local>
CHANTIER3A_DATA_DIR=/srv/data
CHANTIER3A_MEDIA_DIR=/srv/data/media
CHANTIER3A_BASE_URL=https://<URL publique du front ou .onrender.com si test>
CHANTIER3A_KEY_PASSPHRASE=<12+ caractères, à garder>
CHANTIER3A_SESSION_SECRET=<générer>
CHANTIER3A_SECRET_KEY=<générer>
CHANTIER3A_OAUTH_STATE_SECRET=<générer>
CHANTIER3A_PAYMENT_PROVIDERS=manual
CHANTIER3A_PUBLIC_SIGNUP=0
```

Render injecte **`PORT`** ; ne pas définir `CHANTIER3A_ADDR`. Au premier deploy : migrations puis `serve` (entrypoint Docker).

Tester : `https://<billeterie-api>.onrender.com/healthz` puis `https://<billeterie-api>.onrender.com/healthz?db=1` (doit répondre `database: up`). Si `?db=1` renvoie 503, corriger `CHANTIER3A_DATABASE_URL` (Neon : même URL que dans `backend/.env` local).

**Build Docker échoue (`Dockerfile: no such file or directory`)** : Render cherche le Dockerfile à la **racine du dépôt** si **Root Directory** est vide. Corriger l’un des deux :

- **Root Directory** = `backend`, Dockerfile = `Dockerfile`, ou
- laisser la racine vide et utiliser le `Dockerfile` à la racine du monorepo (copie de l’image `backend/`).

### 3. Données festival (obligatoire pour les inscriptions)

La vitrine Vercel affiche un **catalogue statique** ; au moment du checkout l'API charge un **événement publié** dans PostgreSQL. Sans lignes en base, message : *« Aucun événement publié disponible »*.

Une fois par environnement (Neon), exécuter :

```bash
billetterie-api seed-festival
```

- **Render Shell** : disponible sur les plans payants ; sinon exécuter **en local** (ci-dessous) avec la même `CHANTIER3A_DATABASE_URL` Neon que Render.
- **Local** (gratuit) :

```bash
cd backend
cp .env.example .env   # puis URL Neon + KEY_PASSPHRASE identiques à Render
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
billetterie-api seed-festival
```
- Crée l'org `tdev`, l'événement publié `tdev-festival-2026` et les passes `student` / `standard` / `vip` (idempotent).

Vérifier : `GET https://chantier-3a.onrender.com/api/events/` doit lister au moins un événement.

### 4. Suite (optionnel)

SMTP, FedaPay, Google OAuth : voir tableau ci-dessous et [`PRODUCTION-FEDAPAY.md`](PRODUCTION-FEDAPAY.md).

---

## Option alternative : Blueprint

À la racine du dépôt, le fichier [`render.yaml`](../../render.yaml) déclare :

| Ressource | Rôle |
|-----------|------|
| **Web Service** `chantier3a-api` | Image Docker (`backend/Dockerfile`), migrations au démarrage, écoute sur `PORT` |
| **PostgreSQL** `chantier3a-db` | Base obligatoire (`CHANTIER3A_DATABASE_URL`) |
| **Disque 1 Go** monté sur `/srv/data` | Médias uploadés, secret de session fichier, coffre |

### Étapes

1. Pousser le dépôt sur GitHub ou GitLab (branche à déployer).
2. Render : **New** > **Blueprint** > sélectionner le dépôt.
3. Render affiche les ressources du blueprint. Renseigner les variables marquées **sync: false** :
   - **`CHANTIER3A_BASE_URL`** : URL publique du site vue par le navigateur (ex. `https://app.example.com`). Utilisée pour CORS, liens e-mail et retours paiement. Doit pointer vers le front avec `/api` proxifié vers cette API, ou vers l'URL Render de l'API si le front appelle l'API en direct (ajuster CORS si besoin).
   - **`CHANTIER3A_KEY_PASSPHRASE`** : passphrase du coffre de clés (min. 12 caractères, **à conserver** ; perte = billets non vérifiables).
4. **Apply** et attendre le premier déploiement.

Le conteneur exécute `billetterie-api migrate` puis `serve` (voir `docker-entrypoint.sh`). Santé : `GET /healthz`.

### Après le déploiement

| Variable | Quand la renseigner |
|----------|---------------------|
| `CHANTIER3A_SMTP_*` | Envoi des billets PDF par e-mail |
| `CHANTIER3A_FEDAPAY_*` + `CHANTIER3A_PAYMENT_PROVIDERS=manual,fedapay` | Paiement FedaPay ([`PRODUCTION-FEDAPAY.md`](PRODUCTION-FEDAPAY.md)) |
| `CHANTIER3A_GOOGLE_*` | Connexion Google OAuth |
| `CHANTIER3A_CONTACT_TO` | Formulaire contact |

Webhook FedaPay : `https://<nom-service>.onrender.com/api/payments/webhook/fedapay` (ou l'URL publique derrière votre proxy).

## Option manuelle (sans Blueprint)

1. **New PostgreSQL** > noter l'**Internal Database URL**.
2. **New Web Service** > **Docker** :
   - Root directory : `backend`
   - Dockerfile : `Dockerfile`
   - Health check path : `/healthz`
   - Disque persistant : mount `/srv/data` (1 Go minimum)
3. Variables d'environnement minimales :

```env
CHANTIER3A_PYENV=production
CHANTIER3A_DATABASE_URL=<Internal Database URL>
CHANTIER3A_DATA_DIR=/srv/data
CHANTIER3A_MEDIA_DIR=/srv/data/media
CHANTIER3A_BASE_URL=https://votre-domaine-public
CHANTIER3A_KEY_PASSPHRASE=<passphrase-sécurisée>
CHANTIER3A_SESSION_SECRET=<aléatoire>
CHANTIER3A_SECRET_KEY=<aléatoire>
```

Render injecte **`PORT`** ; le backend l'utilise automatiquement (pas besoin de `CHANTIER3A_ADDR`).

## Front et CORS

Par défaut, CORS n'autorise que l'origine `CHANTIER3A_BASE_URL`. En production :

- soit le front est servi sous la même origine publique que `BASE_URL` (reverse proxy `/api` -> Render),
- soit `BASE_URL` est l'origine exacte du front (ex. URL Vercel) si les appels API sont cross-origin.

Voir [`API-FRONTEND.md`](API-FRONTEND.md) et le README backend (section `CHANTIER3A_BASE_URL`).

## Migrations seules

Pour rejouer les migrations sans redémarrer le service :

```bash
# Shell Render ou job one-off avec la même image et DATABASE_URL
billetterie-api migrate
```

Désactiver les migrations au boot (déconseillé sauf pipeline dédié) : `CHANTIER3A_SKIP_MIGRATE=1`.

## Limites Render

- Le plan **Starter** met le service en veille après inactivité (cold start).
- Le disque persistant est lié au service ; sauvegarder Postgres et `/srv/data` en prod.
- Ne pas committer `.env` ; secrets uniquement dans le dashboard Render.

## Vérifier le déploiement

```bash
curl -sS "https://<votre-service>.onrender.com/healthz"
```

Réponse attendue : JSON avec statut OK (voir [`API-FRONTEND.md`](API-FRONTEND.md)).
