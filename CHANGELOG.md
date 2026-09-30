# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Les changements sont regroupés par branche de travail tant qu'ils ne sont pas publiés dans une version.

## [Non publié] — `feat/paiement-integration`

### Ajouté

- **Paiement FedaPay (sandbox et live) via Checkout.js.**
  - Backend : provider `fedapay` (`backend/payments/fedapay.py`). Le serveur crée la transaction (montant = total de la commande, jamais fourni par le client) et ne renvoie au navigateur que son identifiant. Devise **XOF** uniquement.
  - `POST /api/orders` renvoie `payment.client_token` (identifiant de transaction) pour ouvrir le widget.
  - Règlement confirmé côté serveur par `POST /api/payments/verify` (interrogation de l'API FedaPay, contrôle de la référence, du montant et de la devise, échec par défaut en cas de doute) ; émission du billet idempotente.
  - Webhook `POST /api/payments/webhook/fedapay` : signature `X-FEDAPAY-SIGNATURE` (HMAC-SHA256, tolérance 300 s), événement `transaction.approved`, transaction relue via l'API plutôt que crue sur parole.
  - Variables : `CHANTIER3A_FEDAPAY_SECRET_KEY`, `CHANTIER3A_FEDAPAY_WEBHOOK_SECRET`, `CHANTIER3A_FEDAPAY_ENV`.
  - Front (`frontend-web/src/lib/fedapay-checkout.ts`) : chargement du script `checkout.js`, ouverture du widget, interrogation répétée de `verify` tant que le paiement n'est pas confirmé (Mobile Money asynchrone). Variables : `VITE_FEDAPAY_PUBLIC_KEY`, `VITE_FEDAPAY_ENV`.
  - Nouvel écran de succès « Paiement confirmé » ; message distinct quand le paiement n'est pas encore confirmé.
- **Nouveau modèle de billet PDF/PNG** (`backend/notify/ticket_image.py`) : fond noir, carte arrondie à en-tête vert, logo, QR avec logo au centre (correction d'erreur H), perforation à encoches, pied de carte avec identifiant, logo et `#TDev2026`. Police Sora et JetBrains Mono embarquées (licence OFL) dans `backend/notify/assets/`. Un titre trop long passe à la ligne au lieu d'être coupé.
- Exemples générés par `python -m notify.preview_ticket_email` : `backend/notify/previews/billet-exemple.pdf` et `.png`.
- Tests : `backend/tests/test_fedapay.py` (fournisseur, signatures, parcours complet), `backend/tests/test_ticket_image.py` (dimensions, retour à la ligne, décodage du QR).
- Documentation : `TESTING.md` (procédure de test), `backend/docs/PRODUCTION-FEDAPAY.md` (mise en production), et mise à jour de `backend/docs/API-FRONTEND.md`, `backend/docs/PAYMENT-SERVICE.md`, `backend/README.md`, `frontend-web/README.md`, `frontend-web/docs/CONFIGURATION.md`.

### Modifié

- **Les tests utilisent SQLite par défaut** (`backend/tests/sqlite_store.py`) : base jetable par test, aucune dépendance à PostgreSQL. `TEST_DATABASE_URL` permet de tester sur PostgreSQL, uniquement si le nom de la base finit par `_test` (la suite vide les tables). Les variables `CHANTIER3A_*` de `backend/.env` ne sont plus chargées pendant les tests.
- Le lien de l'e-mail de confirmation pointe vers `{CHANTIER3A_BASE_URL}/api/orders/<id>/guest/ticket.pdf?email=…` et le bouton devient « Télécharger mon billet ».
- Création de commande : si le fournisseur de paiement échoue, la commande est annulée et le **stock est rendu** (erreur `400` « payment provider unavailable, please retry ») ; auparavant le stock restait réservé.
- Les webhooks rejoués ou d'un type non géré répondent `200` (le fournisseur n'a pas à réessayer) ; signature invalide ou corps illisible : `400`.
- Le formulaire d'inscription se ferme avant l'ouverture du widget (voir « Corrigé »).
- Les redirections de paiement du front n'acceptent que des URL `https`.

### Corrigé

- **`billetterie-api serve` échouait avec `relation "key_vault" does not exist`** : les migrations étaient annulées à la fermeture de la connexion. Elles s'appliquent maintenant en autocommit (`backend/store/migrate.py`).
- **Widget FedaPay impossible à cliquer** : la modale d'inscription (Radix) laissait `pointer-events: none` sur `body`. Elle est fermée avant l'ouverture du widget.
- **Le logo n'apparaissait jamais sur le billet** (chemin vers un dossier `frontend/` inexistant) et la police retombait sur celle par défaut de Pillow hors Linux. Logo et polices sont désormais dans le dépôt.
- **Lien « billet en ligne » de l'e-mail cassé** : il visait une page (`/order/<id>/billet`) qui n'existe ni dans le front ni dans l'API.
- Règlement refusé si la devise FedaPay est inconnue (résolue via `GET /currencies`, l'API ne renvoie que `currency_id`).

### Supprimé

- `frontend-web/src/lib/payment-checkout.ts` et `order-payment.ts` : ancien flux de paiement par redirection, remplacé par `fedapay-checkout.ts`.

### Sécurité

- Le montant est calculé par le serveur ; le résultat du widget côté navigateur n'a aucun effet sur la commande.
- Aucune clé dans le dépôt : la clé secrète reste dans `backend/.env` (ignoré par git), le front n'a que la clé publique.
- Webhook fermé par défaut : sans secret configuré, tout appel est refusé.

### Vérifié

- Parcours de bout en bout dans un navigateur, contre la vraie sandbox FedaPay : pass gratuit ; pass payant avec paiement accepté (`64000001`) ; paiement refusé (`64000000`, aucun billet) ; fermeture du widget (aucun billet).
- Suite backend : 42 tests passent, 1 échoue (`test_ticket_tdev_and_capability_window`, attente sur `nbf`, échec antérieur à ces changements et non traité).
- QR du billet décodé à l'identique (ZXing et OpenCV) avec une vraie capability de 448 caractères.

### Non vérifié / à faire

- Livraison réelle d'un webhook FedaPay (nécessite un tunnel HTTPS et le secret du webhook) : seule la logique est testée automatiquement.
- Envoi SMTP réel et lecture du QR imprimé par un téléphone ou le scanner de l'entrée.
- Mode `live`.
- Commandes en attente sans expiration : une commande abandonnée garde son stock réservé.
- Le test `test_ticket_tdev_and_capability_window` reste en échec.
- `backend/docker-compose.yml` et `frontend-web/package-lock.json` ont des modifications locales non committées, hors périmètre de ces changements.
