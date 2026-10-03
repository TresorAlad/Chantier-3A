# Billetterie TDEV Festival (frontend)

Application React (Vite, TypeScript, Tailwind) : **vitrine** TDEV Festival (passes, wizard d'inscription 8 étapes) et **dashboard admin** (données API, exports CSV/PDF, équipe).

L'API est fournie par `backend-python/` (FastAPI). En développement, le proxy Vite relaye `/api` vers le backend.

## Prérequis

- Node.js 20+
- Backend billetterie en cours d'exécution (voir `backend-python/README.md`)

## Installation

```bash
cd frontend-web
npm install
cp .env.example .env
# Éditer .env (proxy API, slug événement, etc.)
npm run dev
```

Application par défaut : http://localhost:5173

## Configuration (.env)

Copier `.env.example` vers `.env`. **Ne jamais committer `.env`.**

| Variable | Usage |
|----------|--------|
| `VITE_DEV_API_PROXY` | Cible du proxy dev (`/api` → backend, ex. `http://127.0.0.1:8088`) |
| `VITE_API_URL` | URL API en production si différente de `/api` |
| `VITE_FESTIVAL_EVENT_SLUG` | Slug événement (sinon premier événement publié) |
| `VITE_FEDAPAY_PUBLIC_KEY` | Clé **publique** FedaPay pour le widget Checkout.js (jamais la clé secrète) |
| `VITE_FEDAPAY_ENV` | `sandbox` (défaut) ou `live` |
| `VITE_ADMIN_ROUTE` | Chemin de la page admin (non listée sur la vitrine) |
| `VITE_*_URL` | Réseaux sociaux (URLs HTTPS publiques) |

Détails et bonnes pratiques sécurité : [docs/CONFIGURATION.md](./docs/CONFIGURATION.md).

Le code lit les variables via `src/lib/env.ts` (validation des chemins et URLs).

## Scripts

| Commande | Description |
|----------|-------------|
| `npm run dev` | Serveur de développement |
| `npm run build` | Build production (`dist/`) |
| `npm run preview` | Prévisualiser le build |
| `npm run typecheck` | Vérification TypeScript |

## Architecture (src/)

| Dossier / fichier | Rôle |
|-------------------|------|
| `App.tsx` | Vitrine passes, formulaires, popups de confirmation |
| `main.tsx` | Routes (`/`, admin configurable) |
| `lib/api.ts` | Client HTTP `/api` |
| `lib/env.ts` | Accès sécurisé aux variables `VITE_*` |
| `lib/static-billetterie-catalog.ts` | Contenu landing (passes, prix affichés) sans API |
| `lib/billetterie-storefront.ts` | API au checkout : événement + types de billets réels |
| `lib/billetterie-checkout.ts` | Création commande + verify (gratuit) |
| `components/registration/RegistrationWizard.tsx` | Formulaire PDF V1 (8 étapes, sessionStorage) |
| `lib/registration-form.ts` | Schéma et libellés alignés sur `backend/orders/registration.py` |
| `src/admin/` | Dashboard organisateur (API réelle, pas de mocks) |

Documentation admin : [docs/ADMIN.md](./docs/ADMIN.md).

## Parcours utilisateur

La **landing** utilise un catalogue statique ; le **wizard** collecte le formulaire complet puis appelle l'API a la validation.

1. **Pass Festival (gratuit)** : wizard → `POST /api/orders` avec `buyer.form` → verify → popup succès. **E-mail** avec PDF seulement si SMTP configuré sur l'API (`email_configured` dans `/api/public/site-config`).
2. **Pass Nexus Night (payant, bundle)** : wizard → commande FedaPay → après paiement, billets festival + Nexus ; e-mails selon templates Festival / Nexus.

Logo vitrine et admin : `public/image.png` via `src/components/brand/tdev-brand-assets.ts`.

## Sécurité (résumé)

- Toute variable `VITE_*` est **visible dans le navigateur** : pas de secrets backend dans `.env` frontend.
- `VITE_ADMIN_ROUTE` n'est qu'une URL peu visible ; l'authentification réelle passe par l'API (`backend-python`).
- Ne pas versionner `.env`, `node_modules/`, ni `.cursor/`.

## Dépôt

Projet Chantier 3A : [github.com/TresorAlad/Chantier-3A](https://github.com/TresorAlad/Chantier-3A)
