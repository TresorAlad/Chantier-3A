# Configuration et sécurité (billetterie-frontend)

## Fichiers

| Fichier | Rôle |
|---------|------|
| `.env.example` | Modèle versionné, sans secrets |
| `.env` | Valeurs locales, **ignoré par Git** |
| `src/vite-env.d.ts` | Typage TypeScript de `import.meta.env` |
| `src/lib/env.ts` | Point d'accès unique avec validations |

## Règle Vite

Seules les variables préfixées par **`VITE_`** (ou définies dans `vite.config.ts` pour le proxy) sont lues côté client. Elles sont **incluses dans le JavaScript envoyé au navigateur**.

### Interdit dans `.env` frontend

- Clés API privées (FedaPay secret, SMTP, JWT backend)
- Mots de passe admin
- Tokens de session ou clés de chiffrement

Ces secrets restent dans `backend-python/.env`.

### Autorisé dans `.env` frontend

- URL publiques (API, checkout, réseaux sociaux)
- Slug d'événement, chemin admin (obscurité)
- Cible du proxy de développement (`VITE_DEV_API_PROXY`)

## Variables détaillées

### `VITE_DEV_API_PROXY`

Utilisée par `vite.config.ts` pour proxy `/api` → backend local.

```env
VITE_DEV_API_PROXY=http://127.0.0.1:8088
```

Alternative lue au même endroit : `CHANTIER3A_BASE_URL` (sans préfixe `VITE_`, fichier `.env` racine du projet billetterie).

Redémarrer `npm run dev` après modification.

### `VITE_API_URL`

En production, si l'API n'est pas sur le même domaine sous `/api` :

```env
VITE_API_URL=https://api.example.com/api
```

### `VITE_FESTIVAL_EVENT_SLUG`

Force l'événement affiché (ex. `tdev-festival-2026`). Sinon : premier événement publié retourné par `GET /api/events/`.

### `VITE_FEDAPAY_CHECKOUT_URL`

URL HTTPS de secours pour rediriger l'utilisateur si `POST /api/orders` ne renvoie pas `payment.redirect_url`. Validée dans `env.ts` (http/https uniquement).

### `VITE_ADMIN_ROUTE`

Chemin React Router pour `AdminLogin` (ex. `/acces-admin-billetterie`). Validé :

- doit commencer par `/`
- caractères : lettres, chiffres, `-`, `_`, `/`
- pas de `..`

Valeur par défaut si invalide : `/acces-admin-billetterie`.

### Réseaux sociaux

`VITE_LINKEDIN_URL`, `VITE_YOUTUBE_URL`, etc. : URLs HTTPS optionnelles ; sinon defaults T-Dev dans `public-links.ts`.

## Module `src/lib/env.ts`

Centralise la lecture de `import.meta.env` pour :

- éviter les accès dynamiques non typés
- normaliser les chemins admin
- filtrer les URLs mal formées avant affichage ou redirection

**Convention :** nouveau code qui lit une variable `VITE_*` doit passer par `env.ts` et mettre à jour `.env.example` + `vite-env.d.ts`.

## Proxy (schéma dev)

```text
Navigateur  GET /api/events/...
     |
     v
Vite (5173)  proxy /api
     |
     v
backend-python (8088)
```

## Checklist déploiement

1. `VITE_API_URL` ou reverse proxy `/api` cohérent avec le backend.
2. `VITE_FESTIVAL_EVENT_SLUG` si l'événement cible est fixe.
3. Aucun secret dans les variables `VITE_*`.
4. `.env` absent du dépôt Git (vérifier `.gitignore`).
