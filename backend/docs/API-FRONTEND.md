# Référence API HTTP (frontend)

Document de référence pour intégrer le frontend React contre le backend Python (`billetterie-api`).
Base URL par défaut en dev : `http://127.0.0.1:8080`.

## Conventions

### Préfixe

| Zone | Prefixe |
|------|---------|
| API JSON | `/api` |
| Santé | `/healthz` (hors `/api`) |
| Médias | `/media/{id}` (hors `/api`) |
| SPA | toutes les autres routes servent le frontend |

### Format des erreurs

Réponse JSON :

```json
{
  "error": {
    "code": "invalid_request",
    "message": "texte lisible"
  }
}
```

Codes `error.code` courants : `invalid_request`, `unauthorized`, `forbidden`, `not_found`, `conflict`, `rate_limited`, `internal_error`, `payment_not_confirmed`.

### Authentification

Deux modes compatibles avec le frontend existant :

1. **Bearer (recommandé pour SPA + API cross-origin)**  
   En-tête : `Authorization: Bearer <token>`  
   Le token est renvoyé dans le corps JSON de `POST /api/auth/signup` et `POST /api/auth/login` (`token`).

2. **Cookies**  
   - `chantier3a_session` (HttpOnly)  
   - `chantier3a_csrf` (lisible par JS)  

   Pour toute requête **mutante** (`POST`, `PUT`, `PATCH`, `DELETE`) authentifiée **via cookie**, envoyer aussi :  
   `X-CSRF-Token: <valeur du cookie chantier3a_csrf>`  

   Si vous utilisez le Bearer, le CSRF n'est pas exigé.

### Auth requise

| Symbole | Signification |
|---------|----------------|
| Non | Accessible sans session |
| Oui | Session obligatoire (401 si absent) |
| Role | Session + droit org/evenement (403 si insuffisant) |

Roles org : `owner` > `admin` > `scanner`.

### Montants

Prix en **minor units** (centimes pour EUR), champ `*_minor`.

Dates : **RFC3339** (ex. `2026-04-01T18:00:00Z`).

---

## Meta et configuration

### GET `/healthz`

Auth : Non.

Reponse `200` : `{ "status": "ok" }`

### GET `/api/public/site-config`

Auth : Non.

Reponse `200` :

| Champ | Type | Description |
|-------|------|-------------|
| `community_mode` | bool | Une seule org en mode communautaire |
| `host_scope` | string | Portee d'hebergement |
| `host_name` | string | Nom affiche |
| `host_org` | string | Slug org hote |
| `org_create_disabled` | bool | Creation org desactivee |
| `email_configured` | bool | SMTP configure |
| `public_signup` | bool | Inscription libre (`POST /api/auth/signup`). `false` en prod sauf `CHANTIER3A_PUBLIC_SIGNUP=1` ou mode demo |
| `visitor_checkout_without_account` | bool | Toujours `true` : parcours visiteur sans compte |

### GET `/api/categories`

Auth : Non.

Reponse : `{ "categories": [ { "slug", "label", "count" } ] }`

### GET `/api/currencies`

Auth : Non.

Reponse : `{ "currencies": [ ... ] }`

---

## Auth

### POST `/api/auth/signup`

Auth : Non.

Corps JSON :

| Champ | Type | Obligatoire |
|-------|------|-------------|
| `email` | string | oui |
| `password` | string | oui (longueur minimale cote serveur) |
| `name` | string | non |

Reponse `200` : `{ "user": { id, email, name, created_at, email_verified_at? }, "token": "..." }`  
Erreurs : `400` email/password, `409` email deja pris, `403 forbidden` si `public_signup` est `false` (comptes staff via invite uniquement).

### POST `/api/auth/signup-with-invite`

Auth : Non.

Corps JSON :

| Champ | Type | Obligatoire |
|-------|------|-------------|
| `token` | string | oui (token renvoye par `POST /api/orgs/{org_id}/invites`) |
| `password` | string | oui |
| `name` | string | non |

Reponse `200` : meme forme que signup (session + token). L'utilisateur est membre de l'org avec le role de l'invite.  
Erreurs : `400` invite invalide ou expire, `409` email deja pris (se connecter puis `POST /api/invites/accept`).

### POST `/api/auth/login`

Meme corps que signup (sans exiger `name`).

Reponse `200` : meme forme que signup.  
Erreurs : `401` identifiants invalides.

### POST `/api/auth/logout`

Auth : session (Bearer ou cookie+CSRF).

Reponse `204` sans corps.

### GET `/api/auth/me`

Auth : Oui.

Reponse `200` : `{ "user": { ... } }`

### GET `/api/auth/providers`

Auth : Non.

Reponse : `{ "providers": [] }` (OAuth externe non branche en Python).

### POST `/api/auth/password-reset`

Corps : `{ "email": "..." }`  
Reponse `200` : `{ "ok": true }` (toujours, pour ne pas reveler l'existence du compte).

### POST `/api/auth/password-update`

Corps : `{ "token": "...", "password": "..." }`  
Reponse `200` : `{ "ok": true }`

---

## Evenements (public)

### GET `/api/events/`

Auth : Non.

Query :

| Param | Alias | Description |
|-------|-------|-------------|
| `q` | | Recherche texte |
| `category` | | Filtre categorie |
| `host` | | Slug ou id org hote |
| `from` | `from` | Debut (RFC3339) |
| `to` | | Fin (RFC3339) |
| `limit` | | Max resultats (>= 0) |

Reponse `200` : `{ "events": [ ... ], "host": { scope, name, organisations, multi_org, peers_included, org? } }` (`peers_included` est toujours `false`, legacy.)

### GET `/api/events/{event_id}`

Auth : Non. `event_id` = id ULID ou slug.

Reponse `200` : `{ "event", "ticket_types", "issuer_keys", "gallery": [] }`

Evenement **publie** : accessible sans session. `ticket_types` ne contient que les lignes **actives** (billets, goodies, options) pour le catalogue visiteur.

---

## Organisations

### POST `/api/orgs`

Auth : Oui.

Corps :

| Champ | Type | Obligatoire |
|-------|------|-------------|
| `name` | string | oui |
| `slug` | string | non (derive du name) |
| `default_currency` | string | non (defaut USD) |

Reponse `201` : `{ "org": { id, name, slug, default_currency, role: "owner" } }`

### GET `/api/orgs/{org_id}/events`

Auth : Role scanner+ sur l'org.

Reponse : `{ "events": [ ... ] }`

### GET `/api/orgs/{org_id}/members`

Auth : Role admin+.

Reponse : `{ "members": [ { user_id, name, email, role } ] }`

### GET `/api/orgs/{org_id}/invites`

Auth : Role admin+.

### POST `/api/orgs/{org_id}/invites`

Auth : Role admin+.

Corps : `{ "email": "...", "role": "owner"|"admin"|"scanner" }`  
Reponse `201` : `{ "invite_id", "token", "expires_at" }`

### POST `/api/invites/accept`

Auth : Oui (email du compte = email de l'invite).

Corps : `{ "token": "..." }`  
Reponse : `{ "org_id", "role" }`

### PATCH `/api/orgs/{org_id}/members/{user_id}`

Auth : owner.

Corps : `{ "role": "owner"|"admin"|"scanner" }`

### GET `/api/orgs/{org_id}/bank-account`

Auth : admin+.

### PUT `/api/orgs/{org_id}/bank-account`

Auth : owner.

Corps : `{ "bank_code", "account_number", "account_name" }`

### GET `/api/banks`

Auth : Oui.

Reponse : `{ "banks": [ { code, name } ] }`

### DELETE `/api/invites/{invite_id}`

Auth : admin+ de l'org de l'invite. Reponse `204`.

---

## Evenements (organisateur)

Prefixe commun : `/api/events`.

### POST `/api/events`

Auth : admin+ sur `org_id`.

Corps (creation) :

| Champ | Obligatoire |
|-------|-------------|
| `org_id` | oui |
| `slug` | oui |
| `title` | oui |
| `starts_at` | oui (RFC3339) |
| `ends_at` | oui (RFC3339) |
| `currency` | non (defaut org) |
| `summary`, `description`, `venue_name`, `address`, `timezone`, `category`, ... | non |

Reponse `201` : `{ "event": { ... } }`

### PATCH `/api/events/{event_id}`

Auth : admin+ sur l'evenement. Corps : champs partiels.

### DELETE `/api/events/{event_id}`

Auth : admin+. Reponse `204`. Erreur `409` si billets deja vendus.

### POST `/api/events/{event_id}/publish`

Auth : admin+.

### GET `/api/events/{event_id}/stats`

Auth : scanner+.

Reponse : `{ "stats": { ... } }`

### GET `/api/events/{event_id}/ticket-types`

Auth : admin+.

### POST `/api/events/{event_id}/ticket-types`

Auth : admin+.

Corps typique :

```json
{
  "name": "General",
  "description": "",
  "price_minor": 1500,
  "quantity_total": 100,
  "max_per_order": 5,
  "sales_start": null,
  "sales_end": null,
  "product_kind": "ticket",
  "pass_tier": "student"
}
```

`pass_tier` (optionnel) : `student` (gratuit, `price_minor` 0), `standard` ou `vip` (pas encore activés côté API).

Reponse `201` : `{ "ticket_type": { ... } }`

### GET `/api/pass-tiers`

Catalogue public des passes disponibles à la vente. Pour l'instant : pass étudiant gratuit uniquement.

### PATCH `/api/ticket-types/{tt_id}`

Auth : admin+ sur l'evenement du type.

### DELETE `/api/ticket-types/{tt_id}`

Auth : admin+. Reponse `204`.

### GET `/api/events/{event_id}/admission-conflicts`

Auth : scanner+. Reponse : `{ "conflicts": [] }`

### GET `/api/events/{event_id}/page`

Auth : Oui (implementation actuelle : toujours `404` page non configuree).

### PUT / DELETE `/api/events/{event_id}/page`

Auth : Oui. Meme `404` pour l'instant.

---

## Commandes et paiement visiteur

Parcours **sans compte** : consulter `GET /api/events/` et `GET /api/events/{id}`, creer une commande avec l'email acheteur, regler via le provider (demo : `stub` + `POST /api/payments/verify`), recevoir le mail de confirmation (pass QR pour les produits `product_kind: ticket`, pas de QR pour un goodie seul). Suivi commande : `GET /api/orders/{id}/guest?email=...`. Les comptes utilisateur sont reserves au staff (invite admin) sauf si `public_signup` est active.

### POST `/api/orders`

Auth : Non (si session cookie active, CSRF requis sur POST).

Corps :

```json
{
  "event_id": "ULID",
  "items": [ { "ticket_type_id": "ULID", "quantity": 1 } ],
  "buyer": {
    "email": "a@b.com",
    "first_name": "Prenom",
    "last_name": "Nom",
    "school_name": "Universite / ecole",
    "motivation": "Pourquoi suivre cette edition",
    "wish": "Ce que vous attendez de l'evenement"
  },
  "provider": "manual"
}
```

Pour le **pass etudiant** (`pass_tier: student`), tous les champs `buyer` ci-dessus sont **obligatoires** (sauf `name`, legacy). Les autres types de billets peuvent n'envoyer que `email` et `name`.

`provider` vide = provider par defaut du serveur.

### GET `/api/events/{event_id}/orders` (admin)

Chaque commande inclut un objet **`registration`** avec les reponses du formulaire : `first_name`, `last_name`, `email`, `school_name`, `motivation`, `wish`.

Reponse `201` :

```json
{
  "order": { "id", "event_id", "status", "subtotal_minor", "fee_minor", "total_minor", "currency", "provider", ... },
  "payment": { "provider", "redirect_url", "reference", "instructions" }
}
```

### GET `/api/orders`

Auth : Oui. Liste des commandes de l'utilisateur connecte.

### GET `/api/orders/{order_id}`

Auth : Oui (proprietaire uniquement).

### GET `/api/orders/{order_id}/guest`

Auth : Non.

Query : `email` (obligatoire, meme adresse que `buyer.email` a la commande).

Reponse `200` : `{ "order", "tickets" }` si la commande est payee (`tickets` avec `serial`, `capability` pour les billets).  
Erreurs : `400` email manquant, `404` si id ou email ne correspondent pas (reponse identique pour ne pas fuiter l'existence d'une commande).

### GET `/api/events/{event_id}/orders`

Auth : admin+ sur l'evenement.

### POST `/api/orders/{order_id}/mark-paid`

Auth : admin+ sur l'evenement. Provider **manual** uniquement.

Reponse : `{ "order", "tickets": [ ... ] }`

### POST `/api/orders/{order_id}/mark-failed`

Auth : admin+. Provider manual.

### POST `/api/payments/verify`

Auth : Non.

Corps : `{ "reference": "<order_id>" }`  
Reponse : `{ "order", "tickets" }` ou `402 payment_not_confirmed`.

### POST `/api/payments/webhook/{provider_name}`

Auth : Non (signature provider). Corps brut + en-tetes provider.

Contrat complet backend ↔ microservice paiement (FedaPay, etc.) :
[`docs/PAYMENT-SERVICE.md`](PAYMENT-SERVICE.md).

---

## Billets acheteur

Chaque billet expose :

| Champ | Role |
|-------|------|
| `serial` | Reference publique `TDEV-YYYY-NNNN` (affichage participant, PDF). |
| `capability` | **Contenu exact du QR** : token Ed25519 `chantier3a.<payload>.<sig>` (voir [`PASS-FORMAT.md`](PASS-FORMAT.md)). Pas d'encodage HMAC supplementaire cote front. |

Le payload signe inclut `ref` (meme valeur que `serial`), `nbf` / `exp` alignes sur la fenetre de l'evenement, et `tid` (ULID technique pour l'admission).

### GET `/api/tickets`

Auth : Oui.

### GET `/api/tickets/{ticket_id}`

Auth : Oui (detenteur).

### GET `/api/tickets/{ticket_id}/pdf`

Auth : Non (acces par id; a securiser cote produit si besoin).

Reponse : `text/plain` (placeholder PDF).

---

## Scan porte (en ligne uniquement)

Chaque scan appelle le backend (pas de bundle offline ni de sync différée). Voir [`V1-SCOPE.md`](V1-SCOPE.md).

### POST `/api/scan`

Auth : scanner+.

Corps :

```json
{
  "event_id": "...",
  "capability": "...",
  "device_id": "",
  "gate_id": "",
  "scanned_at": "RFC3339 optionnel"
}
```

Reponse : `{ "result", "reason", "ticket_id" }` avec `result` dans `admitted`, `duplicate`, `invalid`, `wrong_event` (QR pour un autre evenement que `event_id` du corps).

### GET `/api/events/{event_id}/attendees`

Auth : scanner+.

---

## Medias et extras

### POST `/api/events/{event_id}/images`

Auth : admin+. `multipart/form-data`, champ `file` (png/jpeg/webp, max 8 Mo).

Reponse : `{ "image": { id, url: "/media/{id}", width, height } }`

### DELETE `/api/images/{image_id}`

Auth : admin+. Reponse `204`.

### GET `/media/{media_id}`

Auth : Non.

### GET `/api/events/{event_id}/payouts`

Auth : admin+.

---

## OpenAPI interactif

Serveur lance :

- Swagger UI : `/docs`
- Schema machine : `/openapi.json`

---

## Checklist integration frontend

1. Stocker le `token` ou s'appuyer sur cookies ; envoyer `Authorization` sur les appels API si origin separe.
2. Sur mutations avec cookies : lire `chantier3a_csrf` et envoyer `X-CSRF-Token`.
3. Checkout invite : possible sans etre connecte ; eviter de laisser une session cookie d'un autre compte sans CSRF sur le POST `/api/orders`.
4. Montants : toujours afficher a partir de `*_minor` et `currency`. FCFA : code ISO `XOF` (Afrique de l'Ouest) ou `XAF` (Afrique centrale), exposant 0 : `price_minor` = francs entiers (ex. 15 000 FCFA -> `15000`, pas de centimes).
5. Tester le parcours : signup -> org -> event -> ticket-types -> publish -> orders -> mark-paid -> tickets.

Tests automatiques cote backend : `pytest tests/test_api_smoke.py` (dans un venv avec `pip install -e '.[dev]'`).
