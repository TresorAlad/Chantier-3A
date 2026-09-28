# Contrat d'intégration billetterie (Chantier 3A) ↔ microservice paiement

Ce document fixe le contrat entre le backend Python (`billetterie-api`) et un
microservice paiement externe (par ex. Node.js branché sur FedaPay). Le backend
ne détient jamais les fonds : il crée la commande en base, délègue la capture
au MS, puis **settle** (idempotent) n'émet des billets qu'après vérification
**fail closed** du paiement.

Implémentation côté billetterie : `payments/remote.py`, routes
`http_layer/routes/payments.py`. Test de référence : `tests/test_purchase_flow.py`.

## Authentification

- **Backend → MS** : en-tête
  `Authorization: Bearer {CHANTIER3A_PAYMENT_SERVICE_API_KEY}` (ou header défini
  par déploiement).
- **MS → billetterie (webhook)** : signature HMAC-SHA256 du corps brut, en-tête
  `X-Chantier3A-Payment-Signature: sha256={hex}` avec secret
  `CHANTIER3A_PAYMENT_WEBHOOK_SECRET`.

## Backend → microservice

### POST /v1/charges

Démarre un paiement pour une commande déjà créée côté billetterie (`POST /api/orders`).

Corps JSON :

| Champ | Type | Description |
|-------|------|-------------|
| `order_id` | string | Référence billetterie (= `orders.id`, ULID) |
| `amount_minor` | int | Total en unités mineures (ISO 4217 ; pour XOF, exposant 0) |
| `currency` | string | Code ISO 4217 (ex. `EUR`, `XOF`) |
| `buyer_email` | string | E-mail acheteur |
| `buyer_name` | string | Nom affiché |
| `success_url` | string | URL de retour après succès (optionnel) |
| `cancel_url` | string | URL d'abandon (optionnel) |
| `metadata` | object | Métadonnées libres (`event_id`, etc.) |

Réponse `201` :

```json
{
  "reference": "order-id-ulid",
  "status": "pending",
  "redirect_url": "https://pay.example/checkout/...",
  "instructions": ""
}
```

Le frontend redirige l'acheteur vers `redirect_url` (page FedaPay ou autre).

### GET /v1/charges/{reference}

Interroge le statut d'une charge. `{reference}` = en général le même ULID que
`order_id`.

Réponse `200` :

```json
{
  "reference": "order-id-ulid",
  "event_id": "evt-unique-id",
  "status": "paid",
  "amount_minor": 15000,
  "currency": "XOF",
  "paid_at": "2026-03-24T12:00:00Z"
}
```

`status` : `pending` | `paid` | `failed`.

Pour `paid`, `event_id` doit être non vide (anti-rejeu côté billetterie).
`amount_minor` et `currency` doivent correspondre exactement à la commande stockée.

## Microservice → backend (webhook)

Le MS appelle la billetterie :

`POST /api/payments/webhook/{provider}`

où `{provider}` = `CHANTIER3A_PAYMENT_PROVIDER_NAME` (ex. `community-pay`, `fedapay`).

Corps JSON (exemple) :

```json
{
  "reference": "order-id-ulid",
  "event_id": "pay-ms-txn-123",
  "status": "paid",
  "amount_minor": 15000,
  "currency": "XOF",
  "paid_at": "2026-03-24T12:00:00Z"
}
```

Le backend vérifie la signature, réconcilie montant, devise et référence contre
la commande en base, puis appelle settle (idempotent : émission passes, e-mail).

## Polling acheteur (verify)

`POST /api/payments/verify` avec `{ "reference": "<order_id>" }` (sans session).

Le backend appelle `GET /v1/charges/{reference}` sur le MS, réconcilie, puis settle.
Toute ambiguïté → `402 payment_not_confirmed`, jamais de billet émis.

## Variables d'environnement (backend)

| Variable | Rôle |
|----------|------|
| `CHANTIER3A_PAYMENT_SERVICE_URL` | Base URL du MS |
| `CHANTIER3A_PAYMENT_SERVICE_API_KEY` | Clé sortante (backend → MS) |
| `CHANTIER3A_PAYMENT_WEBHOOK_SECRET` | Secret webhook entrant (MS → backend) |
| `CHANTIER3A_PAYMENT_PROVIDER_NAME` | Nom `orders.provider` / segment webhook |
| `CHANTIER3A_PAYMENT_SERVICE_TIMEOUT` | Timeout HTTP secondes (défaut 30) |
| `CHANTIER3A_PAYMENT_PROVIDERS` | Liste allowlist séparée par des virgules ; `manual` reste toujours actif |

Le provider distant n'est enregistré que si `CHANTIER3A_PAYMENT_SERVICE_URL` est
renseigné (`bootstrap.build_payment_registry`).

Exemple `.env` :

```env
CHANTIER3A_PAYMENT_SERVICE_URL=http://payment-ms:3000
CHANTIER3A_PAYMENT_SERVICE_API_KEY=...
CHANTIER3A_PAYMENT_WEBHOOK_SECRET=...
CHANTIER3A_PAYMENT_PROVIDER_NAME=fedapay
CHANTIER3A_PAYMENT_PROVIDERS=manual,fedapay
```

## Fournisseurs locaux (sans MS)

- **manual** : instructions virement + marquer payé / échoué par l'organisateur.
- **free** : commandes à 0 € (pass étudiant, etc.).
- **stub** : auto-règlement en mode `--demo` / tests uniquement.

## Rôle du microservice (FedaPay et autres)

Le MS encapsule la passerelle réelle (clés secrètes, webhooks processeur,
mapping statuts). Exemple FedaPay : créer une transaction, générer le token /
lien de paiement, recevoir `transaction.approved` (signature `X-FEDAPAY-SIGNATURE`),
puis notifier la billetterie via le webhook signé ci-dessus. Voir aussi
`docs/API-FRONTEND.md` (section commandes et paiement visiteur).
