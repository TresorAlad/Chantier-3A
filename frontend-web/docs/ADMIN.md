# Dashboard administrateur (frontend-web)

Interface React sous le chemin configuré par **`VITE_ADMIN_ROUTE`** (ex. `/gestion-dev-local-admin` en production Vercel). L’authentification et les données passent par l’API Render (`/api/admin/...`, cookies ou Bearer selon le flux).

## Accès production

| Élément | Valeur type |
|---------|-------------|
| URL publique | `https://<front-vercel>/<VITE_ADMIN_ROUTE>/login` |
| Build | `VITE_ADMIN_ROUTE` dans `.env.production` ou variable Vercel (ne pas laisser vide : elle écrase le fichier) |
| Redirect racine admin | `vercel.json` : `/gestion-dev-local-admin` → `/login` |
| OAuth Google | `CHANTIER3A_ADMIN_URL` côté backend = URL de base admin (callback) |

Contrôle rapide : ouvrir `GET /api/public/site-config` sur l’API ; `email_configured` indique si les e-mails de billets partent après inscription.

## Branding TDEV

Composants dans `src/admin/components/brand/` :

| Composant | Usage |
|-----------|--------|
| `AdminTdevLogo` | Wordmark (`public/image.png`), variantes `onLight` / `onDark`, tailles `sm` à `xl` |
| `AdminLoadingScreen` | Chargement session, OAuth, chunk admin (`main.tsx` Suspense) |
| `AdminAuthShell` | Carte centrée (invitation équipe) |

Assets partagés vitrine + admin : `src/components/brand/tdev-brand-assets.ts`.

Emplacements principaux : sidebar, header mobile, login, invitation, recherche globale, écran « accès refusé ».

## Fonctionnalités (API réelle)

- **Vue d’ensemble** : statistiques événement courant.
- **Inscrits** : tableau allégé, recherche nom/e-mail, fiche détail avec **formulaire PDF complet** (`registration_form` JSON).
- **Exports** : CSV et PDF depuis les listes (tous les champs du wizard).
- **Commandes / billets / scans** : lecture et actions staff selon rôle org.

Le wizard vitrine (8 étapes) envoie `buyer.form` à `POST /api/orders` ; le backend valide et stocke en `registration_form` (migration `0022_order_registration_form.sql`).

## Pass Nexus 5000 FCFA (bundle)

Achat du pass VIP : le serveur émet **deux billets** (pass festival étudiant + accès Nexus). E-mails distincts Festival / Nexus (templates `backend/notify/ticket_email.py`).

## Développement local

```bash
# frontend-web/.env
VITE_ADMIN_ROUTE=/gestion-dev-local-admin
VITE_DEV_API_PROXY=http://127.0.0.1:8088
```

```bash
npm run dev
# http://localhost:5173/gestion-dev-local-admin/login
```

Staff : compte créé via invitation (`/team`) ou seed backend, pas via inscription publique si `public_signup: false`.
