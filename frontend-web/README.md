# Billetterie TDEV Festival (frontend)

Application React (Vite, TypeScript, Tailwind) dédiée à la **billetterie officielle** : catalogue des passes, inscription gratuite, paiement des passes payants, confirmation par e-mail.

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

## Parcours utilisateur

La **landing** et le **formulaire** fonctionnent sans backend (catalogue statique). L'**API** n'est appelée qu'à la soumission (« Valider l'inscription » / « Continuer vers le paiement »). Goodies : lien externe uniquement.

1. **Pass Festival (gratuit)** : formulaire → API → `POST /api/orders` → verify → popup succès, billet par e-mail.
2. **Pass Nexus Night (payant)** : formulaire → API → commande → redirection paiement si disponible → billet par e-mail.

## Sécurité (résumé)

- Toute variable `VITE_*` est **visible dans le navigateur** : pas de secrets backend dans `.env` frontend.
- `VITE_ADMIN_ROUTE` n'est qu'une URL peu visible ; l'authentification réelle passe par l'API (`backend-python`).
- Ne pas versionner `.env`, `node_modules/`, ni `.cursor/`.

## Dépôt

Projet Chantier 3A : [github.com/TresorAlad/Chantier-3A](https://github.com/TresorAlad/Chantier-3A)
