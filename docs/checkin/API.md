# API de check-in — contrat pour l'app App Scan (3B)

Destinataire : **Rodrigue (lead 3B)** et l'équipe mobile. Auteure : Edéda (back-end check-in).
Statut : implémenté et testé sur PostgreSQL (branche `feat/checkin`). Le schéma OpenAPI exact est dans
[`openapi.json`](openapi.json) (généré par FastAPI, voir « Regénérer » en bas) ; ce document donne les règles et des exemples.

Les valeurs **en gras « à confirmer »** sont des choix par défaut prudents pas encore validés par l'équipe
(voir [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md)). Rien ici n'est une règle métier gelée.

---

## 1. Vue d'ensemble

| Besoin de l'app | Endpoint | Quand |
|---|---|---|
| Savoir quels événements l'agent peut scanner (plus besoin de connaître `event_id`) | `GET /api/checkin/events` | après la connexion |
| Épingler la clé qui signe le snapshot | `GET /api/checkin/signing-key` | à la configuration, puis à chaque changement de `signing_key_id` |
| Télécharger les droits pour décider hors ligne | `GET /api/checkin/snapshot` | à l'ouverture, puis toutes les minutes en ligne (mode delta) |
| Valider un QR **avec réseau** | `POST /api/checkin/scan` | optionnel : si l'app a du réseau au moment du scan |
| Envoyer les scans faits **hors ligne** | `POST /api/checkin/sync` | en tâche de fond, par lots (outbox) |
| Superviseur : conflits, journal, compteurs | `GET /conflicts`, `POST /conflicts/{id}/acknowledge`, `GET /logs`, `GET /stats` | écran superviseur |
| Supervision technique | `GET /health` | sonde |

Préfixe commun : `/api/checkin`. Tout est en JSON UTF-8. Dates : ISO 8601 en UTC avec `Z`
(`2026-10-03T08:01:02Z`) — l'app envoie déjà `toUtc().toIso8601String()` ; une date sans fuseau est lue comme UTC.

### Authentification

`Authorization: Bearer <jeton d'accès>` — le jeton est celui du backend 3A : `POST /api/auth/login` (`{"email", "password"}`) renvoie
`{"user": {...}, "token": "<JWT d'accès>", "refresh_token": "..."}`. Le jeton d'accès **expire** (durée `CHANTIER3A_ACCESS_TOKEN_EXPIRE_MINUTES`) :
l'app doit le **renouveler** avec `POST /api/auth/refresh` (`Authorization: Bearer <refresh_token>`), qui renvoie `{"token", "refresh_token"}` et
**fait tourner** le jeton de renouvellement : conserver le nouveau, l'ancien est invalidé. L'utilisateur doit avoir le rôle **`scanner`** (ou plus)
dans l'organisation de l'événement ; `admin`/`owner` pour les écrans superviseur.
La session Staff définitive (Amélie) remplacera cet adaptateur sans changer ce contrat (port `TerminalAuth`).

```bash
curl -s https://HOST/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"agent@example.com","password":"…"}'
```

### Identifiants à envoyer

| Champ | Règle |
|---|---|
| `event_id` | identifiant (ULID) de l'événement 3A. **Plus de valeur codée en dur** (`TDEV_FESTIVAL_2026`) : il vient de la configuration du terminal. |
| `terminal_id` | UUID stable du terminal (le `terminalId` de `TerminalConfigurations`). Enregistré automatiquement au premier appel. Un terminal est lié à **un** événement. |
| `ticket_id` | le `tid` (ULID) de la capability `chantier3a.<payload>.<sig>` = `tickets.id` côté 3A. |
| `operation_id` | UUID généré **au moment du scan**, conservé tel quel dans l'outbox et dans tous les renvois : c'est la clé d'idempotence. |
| `station` | `EVENT_ENTRY`, `FOOD_ACCESS`, `MERCH_PICKUP`, `AFTER_ENTRY`. **Les deux graphies sont acceptées** : `eventEntry` (ce que l'app envoie aujourd'hui avec `station.name`) et `EVENT_ENTRY`. |
| `decision` | `valid`, `alreadyScanned`, `invalid`, `notAuthorized`, `expired`, `unknown` (graphie Dart actuelle) ou leur forme `snake_case`/`UPPER_SNAKE`. La valeur est stockée **telle quelle** (`reported_decision`). |

---

## 2. Champs à ajouter à l'outbox du 3B

Payload actuel (`drift_scan_event_repository.dart`) : `operation_id, scan_id, ticket_id, participant_id, station, decision,
evaluated_at, previous_scan_at`. Ces 8 champs sont acceptés tels quels. À ajouter :

| Champ | Où | Requis ? | Pourquoi |
|---|---|---|---|
| `event_id` | enveloppe du lot | **oui** | rattacher le lot à l'événement et vérifier les droits |
| `terminal_id` | enveloppe | **oui** | identifier le terminal (audit, conflits, révocation) |
| `batch_id` | enveloppe | **oui** | regroupement pour le support (UUID, nouveau à chaque lot) |
| `device_sent_at` | enveloppe | **oui** | **heure d'envoi sur l'horloge du téléphone, re-calculée à chaque tentative** : sert à corriger l'horloge (§6) |
| `app_version` | enveloppe | recommandé | audit |
| `qr_version` | opération | recommandé | doit valoir `1` (sinon `unsupported_qr_version`) |
| `staff_id` | opération | recommandé | agent qui a scanné (sinon : l'utilisateur de la synchro — faux si l'équipe change avant l'envoi) |
| `capability` | opération | recommandé | contenu du QR : permet au serveur de **re-vérifier la signature**. **Jamais stocké ni journalisé.** Sans lui, `capability_verified = null` et la confiance repose sur le rôle `scanner` du terminal. |
| `pending_count` | enveloppe | optionnel | taille de l'outbox, affichée dans `/stats` |

---

## 3. `POST /api/checkin/sync` — lot hors ligne

```bash
curl -s https://HOST/api/checkin/sync -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{
  "event_id": "01J8ZK8T0M8N0P0Q0R0S0T0U0E",
  "terminal_id": "7d0c6c1e-2b7e-4f0e-9a51-6f0f4e2f6a11",
  "batch_id": "0a9d3e77-5b3a-4a52-9c3e-2f7c1d7c1b10",
  "device_sent_at": "2026-10-03T08:15:00Z",
  "app_version": "0.3.1+12",
  "pending_count": 12,
  "operations": [
    { "operation_id": "b1c2d3e4-0000-4000-8000-000000000001", "scan_id": "e5f6a7b8-0000-4000-8000-000000000001",
      "ticket_id": "01J8ZK8T0M8N0P0Q0R0S0T0U0V", "participant_id": null,
      "station": "eventEntry", "decision": "valid",
      "evaluated_at": "2026-10-03T08:01:02Z", "previous_scan_at": null, "qr_version": 1 }
  ]
}'
```

Limites : **500 opérations maximum** (`batch_too_large`, HTTP 413) ; **taille recommandée : 200**.

### Réponse : un statut par opération, dans l'ordre reçu (HTTP 200)

```json
{
  "batch_id": "0a9d3e77-…", "received_at": "2026-10-03T08:15:00.412Z", "clock_offset_ms": 412,
  "summary": { "accepted": 1, "already_processed": 1, "conflict": 1, "rejected": 1 },
  "results": [
    { "operation_id": "b1c2…", "status": "accepted", "server_decision": "valid", "conflict": null },
    { "operation_id": "c3d4…", "status": "already_processed", "server_decision": "valid", "conflict": null },
    { "operation_id": "d5e6…", "status": "conflict", "server_decision": "already_scanned",
      "conflict": { "type": "CROSS_TERMINAL_DOUBLE_ADMISSION",
                    "winning_terminal_id": "3f2a…", "winning_at": "2026-10-03T08:01:00Z" } },
    { "operation_id": "e7f8…", "status": "rejected", "error_code": "unknown_station",
      "message": "station is not configured for check-in" }
  ]
}
```

| `status` | Sens | Que faire côté app |
|---|---|---|
| `accepted` | journalisé ; le serveur est d'accord (ou ne contredit rien) | marquer l'opération **envoyée** |
| `already_processed` | rejeu : déjà reçue, renvoie le **résultat d'origine**, rien n'est réécrit | marquer **envoyée** |
| `conflict` | journalisée mais **pas gagnante** ou contredite par le serveur (`conflict.type`) | marquer **envoyée** ; afficher/garder l'alerte pour le superviseur. **Ce n'est pas une erreur à réessayer.** |
| `rejected` | **non** journalisée ; `error_code` stable (§7) | **ne pas réessayer** ; marquer `REJECTED`, garder le motif pour le diagnostic |

Un lot **partiellement invalide ne fait jamais échouer tout le lot** : les opérations valides sont traitées, les autres
reçoivent `rejected`. Un champ `flags: ["clock_suspect"]` peut accompagner un `accepted` (horloge douteuse, voir §6).

`conflict.type` : `CROSS_TERMINAL_DOUBLE_ADMISSION` (deux terminaux ont laissé entrer — cas critique), `SAME_TERMINAL_REPLAY`
(doublon local, bénin), `LATE_REVOKED` (billet annulé avant le scan), `NOT_AUTHORIZED_SERVER_SIDE` (le terminal a dit `valid`,
le serveur non), `CLOCK_SUSPECT`. Règles : [`ADR-001-conflits.md`](ADR-001-conflits.md).

**Le serveur ne fait jamais confiance à la décision du terminal** : il la stocke (`reported_decision`) et recalcule la sienne
(`server_decision`). Une opération où le terminal a rapporté autre chose que `valid` est de la *preuve d'audit*, pas une consommation.

### Correspondance des décisions

| Décision 3B (envoyée) | Décision serveur possible |
|---|---|
| `valid` | `valid`, `already_scanned`, `not_authorized`, `revoked`, `unknown`, `wrong_event`, `invalid`, `expired`, `not_yet_valid` |
| `alreadyScanned` | `already_scanned` (ou `valid` si personne n'est encore passé : incohérence signalée dans les stats) |
| `invalid`, `notAuthorized`, `expired`, `unknown` | idem, recalculée par le serveur |

Pour l'affichage d'une réponse en ligne (`/scan`), proposition : `valid`→VALIDE ; `already_scanned`→DÉJÀ SCANNÉ ;
`not_authorized`→NON AUTORISÉ ; `expired`/`not_yet_valid`→EXPIRÉ ; `invalid`/`revoked`/`wrong_event`/`unknown`→INVALIDE.

---

## 3 bis. `GET /api/checkin/events` — événements de l'agent

```bash
curl -s https://HOST/api/checkin/events -H "Authorization: Bearer $TOKEN"
```

```json
{ "events": [ { "event_id": "01J8…E", "title": "TDEV Festival 2026", "slug": "tdev-2026",
                "starts_at": "2026-11-21T08:00:00Z", "ends_at": "2026-11-22T23:00:00Z",
                "timezone": "Africa/Porto-Novo", "role": "scanner" } ] }
```

Seuls les événements **publiés** des organisations où l'utilisateur a au moins le rôle `scanner` sont listés (`role` : `scanner`, `admin` ou `owner`),
triés par date de début. Liste vide = aucun accès. Pas de paramètre `event_id` : c'est l'appel à faire juste après la connexion.

---

## 4. `POST /api/checkin/scan` — scan en ligne

```bash
curl -s https://HOST/api/checkin/scan -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{
  "event_id": "01J8ZK8T0M8N0P0Q0R0S0T0U0E",
  "terminal_id": "7d0c6c1e-2b7e-4f0e-9a51-6f0f4e2f6a11",
  "station": "EVENT_ENTRY",
  "capability": "chantier3a.<payload>.<signature>",
  "operation_id": "b1c2d3e4-0000-4000-8000-000000000002"
}'
```

```json
{ "status": "accepted", "server_decision": "valid", "reason": "", "ticket_id": "01J8…V",
  "serial": "TDEV-2026-0042", "station": "EVENT_ENTRY", "use_index": 0,
  "first_scanned_at": null, "operation_id": "b1c2d3e4-…",
  "participant": { "holder_name": "Awa K.", "pass_type": "vip" } }
```

`participant` (nom du porteur et type de pass, rien d'autre) sert à l'écran de l'agent ; il est `null` si le billet est inconnu ou d'un autre événement.

Doublon : `server_decision: "already_scanned"`, `first_scanned_at` renseigné, `use_index: null`.
La vérification de signature (Ed25519) utilise `tickets/capability.py` du 3A, sans réimplémentation. Le QR n'est jamais stocké.
Renvoyer la **même** requête avec le même `operation_id` renvoie `status: "already_processed"` sans rien réécrire ;
le même `operation_id` avec un contenu différent → HTTP 409 `operation_id_reuse`.
Les raisons `reason` : `bad_signature`, `malformed`, `unknown_kid`, `unsupported_version`, `expired`, `not_yet_valid`,
`wrong_event`, `ticket_revoked`, `station_not_allowed`, `already_scanned`.

---

## 5. `GET /api/checkin/snapshot` — droits pour le cache hors ligne

```bash
curl -s "https://HOST/api/checkin/snapshot?event_id=01J8…E&since_version=4700" \
  -H "Authorization: Bearer $TOKEN" -H 'Accept-Encoding: gzip'
```

| Paramètre | Défaut | Rôle |
|---|---|---|
| `event_id` | — | requis |
| `since_version` | `0` | delta : ne renvoie que les billets dont `version > since_version` |
| `limit` | 2000 (max 5000) | taille de page |
| `cursor` | — | `next_cursor` de la page précédente (la pagination est **figée** sur la version de la 1ʳᵉ page) |

```json
{ "schema_version": 1, "event_id": "01J8…E", "snapshot_version": 4812, "since_version": 4700,
  "generated_at": "2026-10-03T08:00:05Z", "has_more": false, "next_cursor": null,
  "signing_key_id": "snap_Zk3j0vQ1aB",
  "issuer_keys": { "k_If4x36FUomFia_hUBG_SJw": "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo" },
  "entitlements": [
    { "ticket_id": "01J8…V", "serial": "TDEV-2026-0042", "ticket_type_id": "01J8…T",
      "holder_name": "Awa K.", "pass_type": "vip",
      "status": "valid", "stations": ["EVENT_ENTRY"], "uses": { "EVENT_ENTRY": 1 }, "version": 4805 } ] }
```

- **Stockez `snapshot_version`** et renvoyez-le en `since_version` au prochain appel (delta).
- `stations` = postes autorisés ; `[]` si le billet n'est pas `valid`. Les droits sont **réglés par l'organisateur sur le type de billet** :
  `access_event` (`EVENT_ENTRY`, vrai par défaut), `access_food` (`FOOD_ACCESS`), `access_merch` (`MERCH_PICKUP`), `access_after` (`AFTER_ENTRY`),
  faux par défaut, via `PATCH /api/ticket-types/{id}` (le corps doit contenir `name`) ; ils sont lisibles dans `scan_rights` des types de billet.
  Une ligne de `checkin_station_rules` (réglage avancé : plusieurs usages, poste personnalisé) l'emporte sur la case du type.
- `uses` = consommations **déjà connues du serveur** (autres terminaux compris), par poste.
- `issuer_keys` : clés publiques Ed25519 actives de l'événement (`kid` → clé en base64url sans padding) pour vérifier les QR hors ligne.
- `ETag` + `If-None-Match` → `304 Not Modified`. Le corps est compressé en gzip si `Accept-Encoding: gzip`.
- Données personnelles **minimales** : `holder_name` et `pass_type` seulement (jamais d'e-mail, d'école ni de QR).
- **Signature.** Chaque page est signée en Ed25519 : l'en-tête `X-Checkin-Signature: Ed25519; kid=<kid>; sig=<base64url>` couvre **les octets exacts du corps
  non compressé** (droits `stations` et `uses` compris). Rien à re-canoniser : vérifier la signature sur le corps tel qu'il est reçu (après gunzip), avec la clé
  publique obtenue par `GET /api/checkin/signing-key` (`{"algorithm","kid","public_key"}`, base64url) et **épinglée** dans l'app (comparer `kid` à `signing_key_id`).
  **Refuser et ne pas stocker** une page sans signature, ou dont la signature est invalide. Pour détecter une altération au repos, conserver aussi le corps brut
  et l'en-tête de chaque page. Les réponses `304` portent le même en-tête. Sans clé configurée côté serveur, il n'y a pas d'en-tête et `signing-key` répond 404.
- Le serveur recalcule les droits au plus toutes les 15 s ; une modification de règle/billet apparaît donc avec ce délai.

---

## 6. Horloge

Le serveur corrige l'horloge **par lot** : `décalage = heure de réception − device_sent_at`, appliqué à tous les
`evaluated_at` du lot ; le résultat est figé dans le journal. D'où la consigne : **re-horodater `device_sent_at` à chaque tentative d'envoi**
(pas à la création du lot), sinon le décalage inclut le temps d'attente.

Un scan est marqué `clock_suspect` si (valeurs par défaut **à confirmer**) : décalage > 300 s, scan dans le futur de plus de 60 s, ou
plus ancien que 72 h. Un scan suspect **ne peut pas gagner un conflit** contre un scan plausible ; seul, il est accepté et signalé.
L'app n'a rien à corriger elle-même.

---

## 7. Erreurs

Format : `{"error": {"code": "<snake_case>", "message": "<texte>"}}` (HTTP) ou `error_code` dans un résultat `rejected`.
Jamais de QR ni de donnée personnelle dans `message`.

| HTTP | `code` | Sens | Réessayer ? |
|---|---|---|---|
| 400 | `invalid_request` | enveloppe invalide (champ manquant, UUID mal formé…) | non : bug d'intégration |
| 400 | `batch_empty` | `operations` vide | non |
| 400 | `unknown_station` | poste non configuré (`/scan`) | non |
| 401 | `unauthorized` | pas de jeton, jeton expiré ou invalide | **renouveler** le jeton (`/api/auth/refresh`), puis réessayer ; si le renouvellement échoue, se reconnecter |
| 403 | `forbidden` | rôle insuffisant pour cet événement | non |
| 403 | `terminal_revoked` | ce terminal a été révoqué | **non : arrêter l'envoi** et prévenir le superviseur |
| 403 | `terminal_event_mismatch` | terminal déjà rattaché à un autre événement | non |
| 404 | `not_found` | conflit inconnu | non |
| 409 | `operation_id_reuse` | même `operation_id`, contenu différent | non |
| 413 | `batch_too_large` | plus de 500 opérations | **oui, en réduisant la taille du lot** |
| 429 | `rate_limited` | trop de requêtes de ce terminal (600/min par défaut) | oui, avec attente |
| 503 | `service_busy` | base occupée / verrou : `Retry-After` indiqué | **oui** (sans danger : idempotent) |

Codes d'un résultat `rejected` : `operation_invalid` (champ manquant ou invalide ; `message` = champ + règle), `unknown_station`,
`invalid_decision`, `unsupported_qr_version`, `operation_id_reuse`.

---

## 8. Stratégie de retry recommandée

1. **Créer** l'`operation_id` (UUID v4) au moment du scan et le garder pour toute la vie de l'opération.
2. Envoyer par lots de **≤ 200** opérations (les plus anciennes d'abord), quand le réseau revient puis toutes les 15–30 s tant que l'outbox n'est pas vide.
3. Sur chaque résultat : `accepted` / `already_processed` / `conflict` → **envoyé** ; `rejected` → **`REJECTED`** (ne plus réessayer, garder le motif).
4. Sur erreur réseau, `429`, `503`, `5xx` : **réessayer tout le lot** avec attente exponentielle **1 s → 2 → 4 → … → 60 s plafonné, avec jitter ±20 %** ;
   recalculer `device_sent_at` à chaque tentative. Le rejeu est sans danger.
5. Sur `401` : renouveler le jeton (`POST /api/auth/refresh`) puis réessayer ; si le renouvellement échoue, se reconnecter. Sur `413` : diviser le lot par deux. Sur `403 terminal_revoked` : **arrêter**, conserver l'outbox, alerter.
6. Ne jamais réécrire un scan local déjà fait : le serveur est l'autorité en cas de conflit, l'historique local est conservé.

---

## 9. Écrans superviseur (rôle `admin`)

- `GET /api/checkin/conflicts?event_id=&status=open|acknowledged&type=&cursor=&limit=` — plus récents d'abord (curseur `conflict_id`).
- `POST /api/checkin/conflicts/{id}/acknowledge` `{"note": "…"}` — **idempotent** : le premier acquittement (auteur, note, date) est conservé.
- `GET /api/checkin/logs?event_id=&station=&ticket_id=&terminal_id=&since=&cursor=&limit=` — journal d'audit (toutes décisions, jamais de QR).
- `GET /api/checkin/stats?event_id=` — compteurs par poste (`consumed` = consommations canoniques ; `decisions` = journaux par décision serveur),
  conflits ouverts/acquittés, terminaux (`last_seen_at`, `last_batch_at`, `clock_offset_ms`, `pending_count`, `revoked`). Rôle `scanner` suffisant. Mis en cache 2 s.
- `GET /api/checkin/health` — `{"status":"ok","db":"ok","pool":{"size":…,"available":…,"waiting":…}}` ; HTTP 503 si la base ne répond pas.

---

## 10. Exploitation (pour l'équipe, pas pour l'app)

**Règles de postes** (aucune règle par défaut au-delà de `EVENT_ENTRY`). Exemple : repas et after pour le type « VIP » :

```sql
INSERT INTO checkin_station_rules (event_id, ticket_type_id, station, max_uses)
VALUES ('<event_id>', '<ticket_type_id>', 'FOOD_ACCESS', 1),
       ('<event_id>', '<ticket_type_id>', 'AFTER_ENTRY', 1);
-- max_uses = 0 refuse explicitement un poste (y compris EVENT_ENTRY) ; max_uses = 2 autorise une ré-entrée.
```

**Révoquer un terminal** (ses scans déjà journalisés restent ; ses nouveaux lots sont refusés) :

```sql
UPDATE checkin_terminals SET revoked_at = now(), revoked_by = '<qui>' WHERE terminal_id = '<uuid>';
```

**Déploiement** : voir `DESIGN.md` §4.6. Mode autonome recommandé (il n'utilise pas le `Store` à connexion unique du 3A) :
`uvicorn checkin.asgi:app --workers 4` avec `CHECKIN_DATABASE_URL`. Variables : `backend/.env.example` (`CHECKIN_*`).
Mesures de charge : [`PERF.md`](PERF.md).

**Regénérer `openapi.json`** :

```bash
cd backend
python -c "import json; from checkin.asgi import create_standalone_app; print(json.dumps(create_standalone_app().openapi(), indent=2))" > ../docs/checkin/openapi.json
```
