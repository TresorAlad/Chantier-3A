# Hébergement Render (backend API)

Guide pour déployer le backend FastAPI (`backend/`) sur [Render](https://render.com) avec PostgreSQL et stockage persistant pour les médias et le coffre de clés.

## Les inscriptions « disparaissent » après chaque deploy

Les **migrations au démarrage n effacent pas** les commandes ni les billets. Si tout semble vide après un build, l API utilise en pratique **une autre base PostgreSQL** qu avant.

Cas fréquent :

| Cause | Correctif |
|-------|-----------|
| `CHANTIER3A_DATABASE_URL` pointe vers le **Postgres Render** (souvent vide) alors que le seed a été fait sur **Neon** | Dans Environment Render, coller l URL **Neon** (identique a `backend/.env` local). **Save**, redeploy. |
| L URL a ete remplacee par une liaison **fromDatabase** du blueprint | Definir `CHANTIER3A_DATABASE_URL` a la main (`sync: false`), ne pas lier au Postgres Render si vous utilisez Neon. |
| `CHANTIER3A_DEMO=1` en production | Mettre `0` ou supprimer la variable. |

Controle : logs Render au demarrage, ligne `billetterie-api: PostgreSQL cible=.../neondb`. Le **host** doit rester le meme a chaque deploy (ex. `…neon.tech`). Si le host change, les donnees sont sur une autre base.

API : `GET /healthz?db=1` renvoie aussi `database_target` (host/nom de base, sans mot de passe).

**Protection au demarrage** : sur le disque persistant `/srv/data`, l API enregistre la cible PostgreSQL au premier deploy. Si `CHANTIER3A_DATABASE_URL` change ensuite, le service **refuse de demarrer** (au lieu d afficher une billetterie vide). Correctif : remettre l URL Neon d origine. Changement volontaire : une fois `CHANTIER3A_ALLOW_DATABASE_URL_CHANGE=1`, ou supprimer `/srv/data/.chantier3a_db_identity`.

Une seule base de verite : **Neon** pour prod TDEV, avec `KEY_PASSPHRASE` identique au seed local. **Ne pas** activer `CHANTIER3A_DEMO=1` en production.

---

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
CHECKIN_SNAPSHOT_SIGNING_KEY=<générer avec python -m checkin.signing>
CHANTIER3A_PAYMENT_PROVIDERS=manual
CHANTIER3A_PUBLIC_SIGNUP=0
```

`CHECKIN_SNAPSHOT_SIGNING_KEY` est une graine Ed25519 dédiée aux snapshots du contrôle hors ligne. Elle permet au backend de signer les droits et consommations téléchargés par le mobile ; l'application vérifie cette signature avant d'écrire les données localement. Elle ne remplace ni les secrets JWT ni la passphrase du coffre. La générer **une seule fois** depuis `backend/` :

```bash
python -m checkin.signing
```

Copier uniquement la valeur affichée après `CHECKIN_SNAPSHOT_SIGNING_KEY=` dans un secret Render, sans la committer. Après le déploiement, `GET /api/checkin/signing-key` doit répondre `200` avec `algorithm`, `kid` et `public_key`. Si la variable manque, cet endpoint répond `404 signing_not_configured` et le mobile refuse volontairement le snapshot non signé.

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

**E-mails de billets apres inscription** : sans `CHANTIER3A_SMTP_HOST` et `CHANTIER3A_SMTP_FROM`, l'inscription reussit (commande `paid`, billet en base) mais **aucun e-mail n'est envoye** (`notify: SMTP not configured`). Verifier : `GET /api/public/site-config` → `email_configured: true`. Configurer SPF/DKIM pour le domaine expediteur.

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
   - **`CHECKIN_SNAPSHOT_SIGNING_KEY`** : secret Ed25519 généré avec `cd backend && python -m checkin.signing`. Il signe les données hors ligne du mobile et doit rester stable entre les déploiements.
4. **Apply** et attendre le premier déploiement.

Le conteneur exécute `billetterie-api migrate` puis `serve` (voir `docker-entrypoint.sh`). Santé : `GET /healthz`.

### Après le déploiement

| Variable | Quand la renseigner |
|----------|---------------------|
| `CHANTIER3A_SMTP_*` | Envoi des billets PDF par e-mail |
| `CHANTIER3A_FEDAPAY_*` + `CHANTIER3A_PAYMENT_PROVIDERS=manual,fedapay` | Paiement FedaPay ([`PRODUCTION-FEDAPAY.md`](PRODUCTION-FEDAPAY.md)) |
| `CHANTIER3A_GOOGLE_*` | Connexion Google OAuth |
| `CHANTIER3A_CONTACT_TO` | Formulaire contact |
| `CHECKIN_SNAPSHOT_SIGNING_KEY` | Obligatoire pour que le mobile accepte les snapshots hors ligne signés |

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
CHECKIN_SNAPSHOT_SIGNING_KEY=<générer avec python -m checkin.signing>
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
curl -sS "https://<votre-service>.onrender.com/api/checkin/signing-key"
```

Réponses attendues : santé en statut OK (voir [`API-FRONTEND.md`](API-FRONTEND.md)) et clé publique de snapshot avec `algorithm: Ed25519`.
