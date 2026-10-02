# Questions ouvertes — API de check-in

Classées par personne. Pour chaque question : la **valeur par défaut retenue en attendant** (configurable, la plus prudente),
et où elle vit. Rien ici n'est une règle métier validée.

Dernière mise à jour : 2026-10-01.

## Trésor (lead Billetterie, architecte API 3A)

| # | Question | Défaut retenu en attendant |
|---|---|---|
| 1 | `/api/scan` (3A) et `/api/checkin/scan` peuvent admettre le même billet chacun de leur côté. Faut-il écrire aussi dans `admissions` quand `EVENT_ENTRY` est consommé, ou déprécier `/api/scan` pour les terminaux ? | **Aucune écriture dans `admissions`.** Les terminaux 3B n'utilisent que `/api/checkin/*`. |
| 2 | Bugs 2, 3 et 4 (`BUGS_3A.md`) : **j'ai proposé les correctifs dans `feat/checkin`** (code `store/`, `auth/`, `orders/`, commits séparés) ; les validez-vous, ou préférez-vous les faire vous-même ? | Module déployable en **mode autonome** (`checkin.asgi:app`) sans le middleware 3A. |
| 3 | Le 3A est décrit « en ligne uniquement V1 » : acceptez-vous une couche hors ligne/sync dans ce dépôt ? Où est `docs/V1-SCOPE.md` ? | Oui (validé oralement) ; module isolé, aucune modification du comportement existant. |
| 4 | Les « options » (`product_kind = 'option'`, ex. After) créent-elles des billets/QR ? Comment un droit After/Repas est-il représenté côté commande ? | Les droits par poste viennent uniquement de `checkin_station_rules` (par `ticket_type_id`). |
| 5 | `tickets.voided_at` est-il toujours renseigné quand un billet est annulé/remboursé ? Y a-t-il un historique de statuts ? | Statut non valide sans `voided_at` ⇒ considéré annulé **avant** le scan (prudent). |
| 6 | Autorisez-vous `psycopg-pool` dans `pyproject.toml`, `0018_checkin.sql` et le router dans `http_layer/app.py`, et les 2 lignes de `tests/sqlite_store.py` qui ignorent les migrations `-- pg-only` (sinon ma migration casse tous vos tests SQLite) ? Faut-il un mode autonome déployé séparément ? | Oui aux trois (modifications strictement limitées à celles-ci). |
| 7 | `test_ticket_tdev_and_capability_window` échoue avec 1 h d'écart (observation 3) : bug connu ? | Non diagnostiqué ; non corrigé. |
| 9 | Numéros publics `TDEV-YYYY-NNNN` : collisions possibles dans une commande de plusieurs billets, capacité ≈ 10 000/an (`BUGS_3A.md`, observation 4). Connu ? | Collisions dans une commande : **corrigées** sur la branche. La capacité de 10 000/an reste une décision à prendre. |
| 10 | Le limiteur de `/api/scan` (120/min par IP) doit-il rester ainsi sachant que les terminaux d'un site partagent probablement une IP ? | `/api/checkin/*` n'y est pas soumis (limiteur par terminal, 600/min). |
| 11 | Déploiement cible du Jour J : Linux ou Windows ? `uvicorn --workers` est défaillant sous Windows (`PERF.md` §8) ; proxy inverse devant plusieurs processus ? | Recommandation : N processus à 1 worker derrière un proxy inverse, ou `--workers N` sous Linux (à valider). |
| 8 | Comment voulez-vous que les règles de postes (`checkin_station_rules`) soient alimentées : SQL, script, futur back-office ? | SQL/script documenté dans `API.md` ; pas d'endpoint d'édition. |
| 9 | **L'inscription par mot de passe et par invitation échoue (HTTP 500) sur `main`** : `auth.service.signup` et `signup_with_invite` appellent `create_user(st, email, hash, nom)` alors que `store/users.py` attend un `UserPartial` (`BUGS_3A.md`, bug 4). **Corrigé sur la branche** (`auth/service.py`). Comment les comptes des agents de scan seront-ils créés (Google OAuth ? invitation ?) | Je ne dépends pas de ces routes ; je valide les JWT existants. |
| 10 | Les jetons d'accès JWT sont de courte durée (`CHANTIER3A_ACCESS_TOKEN_EXPIRE_MINUTES`). Un terminal hors ligne pendant des heures aura un jeton expiré à la synchro : le renouvellement (`/api/auth/refresh`) suffit-il, ou faut-il un jeton longue durée réservé aux terminaux ? | Le module valide les JWT du 3A tels quels ; l'app renouvelle le jeton avant d'envoyer (`API.md`). |
| 12 | **Clé de signature du snapshot** (demande de Rodrigue : signer les droits `stations` et `uses`). Le module signe en Ed25519 avec une clé **dédiée** (`CHECKIN_SNAPSHOT_SIGNING_KEY`, graine base64url ; la générer avec `python -m checkin.signing`). Qui la génère et la range (variable d'environnement Render, secret) ? Sans clé, le snapshot est servi non signé et l'app doit le refuser. | Aucune clé n'est dans le dépôt. Les tests utilisent une clé éphémère. |
| 13 | La branche reprend de la PR #3 de Rodrigue les 4 colonnes de droits par type de billet (`access_event/food/merch/after`, migration `0019`) et la vérification base64url canonique de `tickets/capability.py`. Elle ne reprend **pas** son `/api/scan/sync`, `scan-bundle`, ni les changements de `/api/scan` (le check-in passe par `/api/checkin/*`). Validez-vous cette répartition, et la renumérotation de ses migrations (`0018`/`0019` en collision) si sa PR doit coexister ? | `/api/scan` reste comme sur `main`. |

## Rodrigue (lead 3B)

| # | Question | Défaut retenu |
|---|---|---|
| 1 | L'outbox doit ajouter `event_id`, `terminal_id`, `batch_id`, `device_sent_at`, `app_version`, `qr_version` ; et idéalement `staff_id`, `capability`, `pending_count`. Acceptez-vous ? | Champs requis côté serveur sauf `staff_id`, `capability`, `pending_count`, `participant_id` (optionnels). |
| 2 | `decision.name` / `station.name` de Dart sont en camelCase (`alreadyScanned`, `eventEntry`) alors que les docs disent `ALREADY_SCANNED`, `EVENT_ENTRY`. Quelle graphie est finale ? | `/sync` accepte les deux, normalise en `UPPER_SNAKE` (stations) / `snake_case` (décisions). `reported_decision` stocké verbatim. |
| 3 | Re-horodater `device_sent_at` à **chaque tentative d'envoi** ? | Recommandé dans `API.md` ; le serveur ne peut pas l'imposer. |
| 4 | Que faire d'un lot `403 terminal_revoked` et d'un `503 service_busy` ? Stratégie de retry (backoff, taille de lot) ? | `API.md` : backoff exponentiel 1 s → 60 s avec jitter, lot ≤ 200, arrêt des retries sur `terminal_revoked`. |
| 5 | Quel identifiant est envoyé comme `ticket_id` : le `tid` (ULID) de la capability 3A ? Le `participant_id` a-t-il un équivalent ? | `ticket_id` = `tid` ULID du 3A ; `participant_id` optionnel, stocké tel quel (`participant_ref`), jamais utilisé en décision. |
| 6 | Le `terminal_id` (UUID de `TerminalConfigurations`) survit-il à une réinstallation ? | Non supposé : un nouveau `terminal_id` = nouveau terminal. |
| 7 | L'app enverra-t-elle l'état `pending_count` pour alimenter `/stats` ? | Champ optionnel dans l'enveloppe de `/sync`. |

## Romain (BDD 3A)

| # | Question | Défaut retenu |
|---|---|---|
| 1 | `feature/bdd-romain` (schéma SERIAL/HMAC, vues analytiques) est-elle abandonnée au profit de `backend/migrations/` ? | Oui : seul le schéma des migrations (0001–0017 actuellement) est pris en compte. |
| 2 | Qui possède la numérotation des migrations (0018+) ? Conflit possible si d'autres PR ajoutent `0018`. | `0018_checkin.sql` ; renumérotée si besoin avant fusion. |
| 3 | Volumes réels (participants, terminaux, scans/min) ? Purge/rétention des `scan_logs` après l'événement ? | Hypothèses de charge de `DESIGN.md` §4.1, mesures dans `PERF.md` ; aucune purge. |
| 4 | Faut-il des vues pour le dashboard (stats par poste, conflits) ? | Non dans ce périmètre ; `/stats` seulement. |

## Daniel (sécurité / signature QR)

| # | Question | Défaut retenu |
|---|---|---|
| 1 | Format QR officiel : `chantier3a.<payload>.<sig>` (3A) pour tous ? Le brouillon 3B `tdev.ticket.dev` est-il abandonné ? | Seul le format 3A est vérifié côté serveur (`tickets/capability.py`, inchangé). |
| 2 | Clés publiques : comment le mobile les récupère-t-il et comment gère-t-on la rotation/révocation de `kid` ? | Clés actives de l'événement dans `/snapshot` (`issuer_keys`), via les fonctions 3A. |
| 3 | Le terminal doit-il envoyer la `capability` dans `/sync` pour permettre la re-vérification serveur (sans jamais la stocker) ? | Optionnelle ; absente ⇒ `capability_verified = NULL` et confiance dans le rôle `scanner`. |
| 4 | Faut-il journaliser le hash de la capability (traçabilité) ? | Non : jamais de QR brut ni de hash de QR journalisé. |

## Cédric (data ; pont Shop / Billetterie → App Scan)

| # | Question | Défaut retenu |
|---|---|---|
| 1 | Qui produit le snapshot des droits (`access_food`, `access_after`, `has_merch`) et à partir de quelle source ? | `checkin_station_rules` + `tickets` du 3A uniquement. |
| 2 | Comment relier une commande du Shop (chantier 2) à un billet ou à un droit `MERCH_PICKUP` ? Format de QR du Shop ? | Non géré ; `MERCH_PICKUP` refusé sans règle explicite. |
| 3 | `participant_id` : quelle source ? Le 3A n'a que `buyer_email` / `holder_name`. | Facultatif, stocké sans usage. |
| 4 | Événements analytiques attendus (tracking plan V1.0.0) : `scan_logs` suffit-il ? | Oui ; tous les scans journalisés avec toutes les décisions. |

## Amélie (sessions staff)

| # | Question | Défaut retenu |
|---|---|---|
| 1 | La session Staff réutilise-t-elle les sessions/rôles 3A (`scanner`) ou un jeton propre à l'app ? | Adaptateur `Sessions3AAuth` (3A) derrière le port `TerminalAuth`. |
| 2 | Comment relier le `staff_id` d'un scan hors ligne (session active au moment du scan) à un utilisateur ? | `staff_user_id` = `staff_id` envoyé s'il existe, sinon l'utilisateur authentifié de la synchro. |
| 3 | Révocation d'un staff : que devient son terminal ? | Indépendant (révocation par terminal uniquement). |

## Marina-Gracia (règles de scan)

| # | Question | Défaut retenu |
|---|---|---|
| 1 | Ré-entrée : un billet peut-il entrer plusieurs fois ? | `max_uses = 1` (aucune ré-entrée). |
| 2 | Règles de consommation de chaque poste (repas, merch, after) : une fois chacun ? Délai minimal entre deux scans ? | Une fois par poste ; aucun délai. |
| 3 | Quels types de billets donnent accès à quels postes ? | Seul `EVENT_ENTRY` autorisé par défaut ; le reste par `checkin_station_rules`. |
| 4 | Liste finale des postes et leurs identifiants (zones/terminaux) ? | `EVENT_ENTRY, FOOD_ACCESS, MERCH_PICKUP, AFTER_ENTRY` (configurable `CHECKIN_STATIONS`). |
| 5 | Que faire quand un droit est épuisé (message, exception superviseur) ? | `already_scanned` ; aucune exception. |

## Abdoul-Rachid (sécurité terrain)

| # | Question | Défaut retenu |
|---|---|---|
| 1 | Seuils d'horloge suspecte : décalage max (300 s ?), tolérance futur (60 s ?), âge max d'un scan (72 h ?). | `CHECKIN_CLOCK_OFFSET_MAX_SECONDS=300`, `CHECKIN_CLOCK_FUTURE_TOLERANCE_SECONDS=60`, `CHECKIN_MAX_OPERATION_AGE_HOURS=72`. |
| 2 | Terminal révoqué : refuse-t-on aussi les scans faits **avant** la révocation mais non encore synchronisés ? | Oui, tout nouveau lot refusé (prudent) ; anciens scans restent journalisés. |
| 3 | Scénarios de fraude à couvrir (2 terminaux, horloge truquée, rejeu de lot, QR copié) et simulations Jour J. | Couverts : rejeu (idempotence), horloge (`clock_suspect`), double admission (conflit). **Non couvert** : QR copié présenté à deux portes hors ligne simultanément (seulement *détecté* a posteriori). |
| 4 | Limite de débit par terminal/IP (les portes partagent probablement une IP). | 600/min par terminal ; pas de limite par IP seule. |
| 6 | Acceptez-vous les compromis de cache (clé publique révoquée acceptée jusqu'à 30 s par processus ; cache d'authentification désactivé par défaut) ? | `CHECKIN_KEYS_TTL_SECONDS=30`, `CHECKIN_AUTH_CACHE_SECONDS=0`. |
| 5 | Qui peut révoquer un terminal et comment (endpoint ? SQL ?) | SQL documenté ; pas d'endpoint. |

## Chantier 2 (Shop)

| # | Question | Défaut retenu |
|---|---|---|
| 1 | Format du QR du Shop, signature, clés. | Non géré. |
| 2 | Base, API et source de vérité des commandes de goodies / droits de retrait. | Non géré ; aucun accès au Shop. |
| 3 | Les goodies vendus au 3A (`product_kind = 'goodie'`) et ceux du Shop (`shop.tdevfestival.com`) sont-ils le même catalogue ? | Non supposé. |

## API centrale (non spécifiée — **rien n'est codé**)

Ce qu'il faudrait savoir avant de la construire :

1. **Qui la demande et pour quels flux précis** (Shop → droits ? billetterie → dashboard ? paiement → e-mail ?). Définition écrite du besoin.
2. Quelles **données** sont maîtres (billets, participants, commandes de goodies, droits), et qui les possède (Trésor ? Cédric ? chantier 2 ?).
3. **Identifiants communs** : clé de participant/billet partagée entre 3A, Shop et 3B ; format de QR unique.
4. **Contrats** : OpenAPI des autres chantiers, authentification inter-services, versionnement, politique de dépréciation.
5. **Modes d'échange** : HTTP synchrone, webhook, import par fichier ou base partagée ? (Le plan de repli CIBLE B exclut toute base partagée avec le 3A.)
6. **Disponibilité et charge** le Jour J : quels services doivent fonctionner hors ligne, SLA, propriétaires d'astreinte.
7. **Sécurité** : secrets inter-services, rotation, journalisation sans donnée personnelle.
8. **Gouvernance** : qui arbitre les conflits de contrat, qui fusionne, où vit le code (dépôt).

Le module check-in est conçu pour s'y brancher sans réécriture : ports `TerminalAuth` et `TicketSource`
(adaptateur « fichier snapshot JSON » prévu pour le plan de repli CIBLE B), contrats versionnés
(`/api/checkin`, `qr_version`, `schema_version`).
