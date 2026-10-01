# API de check-in — conception (TDEV-54, TDEV-55, TDEV-56)

Statut : **proposition Phase 1, à valider (GO) avant toute implémentation.**
Auteure : Edéda BLEOUSSI (chantier 3B, Dev Logique Back-end & Validation BDD).
Cible : module isolé `backend/checkin/` dans ce dépôt, branche `feat/checkin`, PR relue par Trésor.

Légende : **[VU]** constaté dans le code · **[CHOIX]** décision de conception proposée ·
**[SUPPOSÉ]** hypothèse à confirmer (détail dans `OPEN_QUESTIONS.md`).

---

## 0. Écarts entre le contexte reçu et le code (le code fait foi)

| # | Constat [VU] | Conséquence pour le module |
|---|---|---|
| 1 | `migrate_postgres()` ne fait jamais de commit : la base reste vide (`BUGS_3A.md`, bug 1). | Mes tests appliquent `0014` via un helper qui valide explicitement. La migration elle-même reste un fichier SQL standard. |
| 2 | Le `session_middleware` de `http_layer/app.py` s'exécute **avant toute route** (y compris `/api/checkin/*`) et utilise la connexion unique du `Store`. Un doublon sur `/api/scan` la bloque (bug 2). | Mon pool dédié protège *mes requêtes SQL*, **pas** le middleware. Tant que le bug 2 n'est pas corrigé, le module monté dans l'app 3A n'est pas fiable sous charge. D'où le mode « autonome » (§4.6). **Je corrige ma précédente affirmation** « le module n'est pas touché ». |
| 3 | `Store.execute*()` fait un `commit()` à **chaque appel** (`store/store.py`). | Je n'utilise le `Store` que pour des **lectures** (sur une connexion du pool, hors transaction d'écriture). Toute écriture du module passe par mes propres transactions. |
| 4 | Le 3B sérialise `decision.name` et `station.name` de Dart (`drift_scan_event_repository.dart`) : valeurs **camelCase** (`alreadyScanned`, `eventEntry`…), alors que les docs 3B écrivent `ALREADY_SCANNED`, `EVENT_ENTRY`. | `/sync` accepte les deux graphies et normalise (§2.8). À faire confirmer par Rodrigue. |
| 5 | Le 3A stocke ses dates en `TEXT` ISO (`…Z`), pas en `timestamptz`. | Mes nouvelles tables utilisent `timestamptz`. Conversion via `store/timeutil.py`. |
| 6 | `ScanRateLimitMiddleware` ne limite que les chemins `/api/scan*` (120/min/IP). | `/api/checkin/*` n'est pas limité. Je prévois un limiteur **par terminal** dans le module (§2.9). |
| 7 | Le payload d'outbox 3B n'a pas `event_id`, `terminal_id`, `staff_id`, `qr_version`, `app_version`. | Champs à ajouter listés en §2.3 (demande à Rodrigue). |
| 8 | `docs/V1-SCOPE.md`, `BILLETTERIE-3A-ARCHITECTURE.md`, `CLUSTERING.md` (cités par les README) sont introuvables. | Le périmètre « V1 en ligne uniquement » du 3A n'est pas vérifiable. Question à Trésor. |
| 9 | Suite existante sur base migrée : 21 passed, 2 failed (bug 2 + observation 3). | Ma base de référence avant toute modification. |

---

## 1. Modèle de données (migration `0014_checkin.sql`)

Principes [CHOIX] :
- Nouvelles tables préfixées `checkin_` / `scan_` ; aucune table du 3A n'est modifiée.
- Horodatages en `timestamptz`. Identifiants 3A en `TEXT` (ULID) pour pouvoir référencer `tickets(id)`.
- **Les journaux ne portent pas de `FOREIGN KEY … ON DELETE CASCADE`** vers `events` : supprimer un
  événement (`DELETE /api/events/{id}` existe) ne doit pas effacer un journal « immuable ».
  Les tables *dérivées* (consommations, droits, règles) cascadent.
- Stations : `TEXT` validé par format (`^[A-Z][A-Z0-9_]{1,31}$`), pas un `ENUM` SQL : la liste
  finale des postes n'est pas gelée (Marina-Gracia / Amélie). Liste connue configurable
  (`CHECKIN_STATIONS`, défaut : les 4 postes du 3B).

### 1.1 `checkin_terminals`

```sql
CREATE TABLE checkin_terminals (
    terminal_id     uuid PRIMARY KEY,              -- fourni par l'app (TerminalConfigurations.terminalId)
    event_id        text NOT NULL,
    label           text NOT NULL DEFAULT '',
    default_station text,
    registered_by   text,                          -- users.id (sans FK : on garde l'historique)
    first_seen_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at    timestamptz NOT NULL DEFAULT now(),
    clock_offset_ms bigint,                        -- dernier décalage brut observé (diagnostic uniquement)
    revoked_at      timestamptz,
    revoked_by      text
);
CREATE INDEX idx_checkin_terminals_event ON checkin_terminals (event_id, last_seen_at DESC);
```
Enregistré au premier appel authentifié (§5). `clock_offset_ms` ne sert **pas** à corriger les
scans (voir §3 : le décalage utilisé est celui *du lot*, figé dans `scan_logs`).

### 1.2 `checkin_station_rules`

```sql
CREATE TABLE checkin_station_rules (
    event_id       text NOT NULL REFERENCES events(id)       ON DELETE CASCADE,
    ticket_type_id text NOT NULL REFERENCES ticket_types(id) ON DELETE CASCADE,
    station        text NOT NULL CHECK (station ~ '^[A-Z][A-Z0-9_]{1,31}$'),
    max_uses       integer NOT NULL DEFAULT 1 CHECK (max_uses >= 0),
    PRIMARY KEY (event_id, ticket_type_id, station)
);
```
Règle **par défaut prudente** (implémentée dans `domain.py`, pas en base) :
- `EVENT_ENTRY` est autorisé avec `max_uses = 1` pour tout billet `valid` de l'événement **s'il n'existe aucune ligne** pour (événement, type, `EVENT_ENTRY`).
- Tout autre poste est **refusé** sans ligne explicite.
- Une ligne avec `max_uses = 0` refuse explicitement (y compris `EVENT_ENTRY`).
- `max_uses > 1` = ré-entrée ou consommations multiples autorisées (valeur par défaut 1 : pas de ré-entrée — à valider avec Marina-Gracia).

Alimentation : pas d'endpoint d'édition dans ce périmètre ; insertion par SQL / script
documenté (`API.md`). *Les droits repas / after / merch ne sont pas gelés* : cette table les
remplace par une configuration explicite, sans inventer de règle.
[SUPPOSÉ] Les « options » payantes (`product_kind = 'option'`) ne créent pas de billet (rien ne le
montre dans `orders/`, à confirmer par Trésor/Cédric) ; elles ne peuvent donc pas, aujourd'hui,
ouvrir un poste par cette table.

### 1.3 `scan_logs` — journal **immuable** de tous les scans

```sql
CREATE TABLE scan_logs (
    log_id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id           uuid    NOT NULL UNIQUE,         -- clé d'idempotence
    scan_id                uuid,                            -- id local 3B (audit)
    payload_hash           bytea   NOT NULL,                -- SHA-256 du payload canonique (détecte la réutilisation d'operation_id)
    event_id               text    NOT NULL,
    ticket_id              text,                            -- sans FK : un terminal peut envoyer un id inconnu
    participant_ref        text,                            -- participant_id 3B (aucun équivalent dans le 3A)
    terminal_id            uuid    NOT NULL,
    staff_user_id          text,
    station                text    NOT NULL,
    reported_decision      text,                            -- décision du terminal, VERBATIM (NULL pour un scan en ligne)
    reported_valid         boolean NOT NULL,                -- dérivé à l'insertion (index)
    server_decision        text    NOT NULL,                -- recalculée par le serveur (§2.8)
    server_reason          text    NOT NULL DEFAULT '',
    capability_verified    boolean,                         -- NULL = capability non fournie
    is_claim               boolean NOT NULL,                -- participe à la consommation (§3)
    ack_status             text    NOT NULL CHECK (ack_status IN ('accepted','conflict')),  -- figé : ce qu'on a répondu
    device_evaluated_at    timestamptz,
    device_sent_at         timestamptz,
    server_received_at     timestamptz NOT NULL,
    clock_offset_ms        bigint  NOT NULL DEFAULT 0,      -- décalage du LOT, figé
    corrected_evaluated_at timestamptz NOT NULL,
    clock_suspect          boolean NOT NULL DEFAULT false,
    clock_suspect_reason   text    NOT NULL DEFAULT '',
    app_version            text    NOT NULL DEFAULT '',
    qr_version             integer,
    connection_status      text    NOT NULL CHECK (connection_status IN ('online','offline_synced')),
    batch_id               uuid
);
-- Immuabilité : toute modification est refusée en base, pas seulement par convention.
CREATE FUNCTION scan_logs_immutable() RETURNS trigger LANGUAGE plpgsql AS
$$ BEGIN RAISE EXCEPTION 'scan_logs is append-only'; END $$;
CREATE TRIGGER trg_scan_logs_immutable
    BEFORE UPDATE OR DELETE ON scan_logs FOR EACH ROW EXECUTE FUNCTION scan_logs_immutable();
```

Écarts avec la proposition initiale, justifiés :
- `id` → `log_id bigint identity` : clé monotone, idéale pour la pagination par curseur (`/logs`) et
  pour un index btree compact ; `operation_id` reste l'identifiant d'idempotence.
- `ack_status`, `is_claim`, `payload_hash`, `reported_valid`, `clock_offset_ms`, `clock_suspect*`,
  `capability_verified` ajoutés : ils figent **au moment de l'insertion** tout ce qui doit
  rendre la résolution déterministe (§3) et rejouable sans recalcul.
- **Pas de `UPDATE` du journal** : le décalage d'horloge est calculé à l'insertion (par lot). Le
  « gagnant » vit dans `station_consumptions`/`scan_conflicts`, jamais dans `scan_logs`.

**Partitionnement : non.** Volume estimé [SUPPOSÉ] : 3 000 participants × 4 postes × ~1,5 scan ≈ 20 000 lignes par
événement. Une partition n'apporte rien sous ~10 M de lignes et complique les contraintes
d'unicité globale (`operation_id`). Seuil de réévaluation : > 10 M lignes ou besoin de purge par date.

### 1.4 `station_consumptions` — consommation canonique

```sql
CREATE TABLE station_consumptions (
    ticket_id      text    NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    station        text    NOT NULL,
    use_index      integer NOT NULL CHECK (use_index >= 0),
    event_id       text    NOT NULL,
    winning_log_id bigint  NOT NULL REFERENCES scan_logs(log_id),
    consumed_at    timestamptz NOT NULL,        -- = corrected_evaluated_at du gagnant
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ticket_id, station, use_index)  -- = UNIQUE (ticket, station, use_index)
);
```
`use_index < max_uses` ne peut pas être un `CHECK` (la valeur est dans une autre table) : imposé par
`domain.py` et couvert par des tests. La base garantit l'unicité, donc « exactement un gagnant par
(ticket, station, use_index) » même en cas de bug applicatif.

### 1.5 `scan_conflicts`

```sql
CREATE TABLE scan_conflicts (
    conflict_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id       text   NOT NULL,
    ticket_id      text,
    station        text   NOT NULL,
    winning_log_id bigint REFERENCES scan_logs(log_id),     -- NULL si le perdant n'a jamais pu prétendre à la consommation
    losing_log_id  bigint NOT NULL UNIQUE REFERENCES scan_logs(log_id),
    type           text   NOT NULL CHECK (type IN ('CROSS_TERMINAL_DOUBLE_ADMISSION','SAME_TERMINAL_REPLAY',
                                                   'LATE_REVOKED','NOT_AUTHORIZED_SERVER_SIDE','CLOCK_SUSPECT')),
    clock_suspect  boolean NOT NULL DEFAULT false,
    detected_at    timestamptz NOT NULL DEFAULT now(),
    status         text   NOT NULL DEFAULT 'open' CHECK (status IN ('open','acknowledged')),
    note           text   NOT NULL DEFAULT '',
    resolved_by    text,
    resolved_at    timestamptz
);
```
Écart justifié : **une ligne par perdant** (`losing_log_id UNIQUE`) plutôt qu'un tableau
`losing_log_ids`. Un tableau rend l'upsert idempotent et l'acquittement par perdant pénibles, et
ne s'indexe pas. Pour un (ticket, station), on retrouve les perdants par l'index
`(ticket_id, station)`. Un conflit n'est **jamais supprimé** : un journal ne fait que grossir, donc
un perdant le reste (monotonie, voir ADR-001).

### 1.6 Droits pré-calculés pour le snapshot

```sql
CREATE SEQUENCE checkin_version_seq;
CREATE TABLE checkin_entitlements (
    event_id       text   NOT NULL,
    ticket_id      text   NOT NULL,
    serial         text   NOT NULL,
    ticket_type_id text   NOT NULL,
    status         text   NOT NULL,              -- valid | void | refunded (3A)
    stations       text[] NOT NULL,              -- postes autorisés (règles + défaut prudent)
    uses           jsonb  NOT NULL DEFAULT '{}', -- {"EVENT_ENTRY": 1}
    content_hash   text   NOT NULL,
    version        bigint NOT NULL,              -- nextval(checkin_version_seq) quand le contenu change
    PRIMARY KEY (event_id, ticket_id)
);
CREATE INDEX idx_checkin_entitlements_delta ON checkin_entitlements (event_id, version, ticket_id);
CREATE TABLE checkin_snapshot_meta (
    event_id     text PRIMARY KEY,
    refreshed_at timestamptz NOT NULL,
    max_version  bigint NOT NULL DEFAULT 0
);
```
Pas de trigger sur les tables 3A (ce serait modifier leur comportement) : le rafraîchissement est
*tiré* (pull) par le module, avec TTL (§2.1).

### 1.7 Index et requêtes servies

| Table | Index | Requête servie |
|---|---|---|
| `scan_logs` | `UNIQUE(operation_id)` | idempotence : `INSERT … ON CONFLICT (operation_id) DO NOTHING RETURNING` |
| `scan_logs` | `(ticket_id, station, corrected_evaluated_at, operation_id) WHERE is_claim` (partiel) | classement des prétendants d'un (ticket, station) pendant la résolution — **chemin critique** |
| `scan_logs` | `(event_id, log_id)` | `/logs` (pagination par curseur sur `log_id`, filtre événement) |
| `scan_logs` | `(terminal_id, server_received_at DESC)` | `/logs?terminal_id=`, `/stats` (dernière activité par terminal) |
| `scan_logs` | `(event_id, station, server_decision)` *(à valider par EXPLAIN — optionnel)* | `/stats` (`GROUP BY station, server_decision`) |
| `station_consumptions` | PK `(ticket_id, station, use_index)` | consommation atomique, détection d'épuisement |
| `station_consumptions` | `(event_id, station)` | `/stats` (compte par poste), snapshot (`uses`) |
| `station_consumptions` | `(winning_log_id)` | lien log → consommation (audit) |
| `scan_conflicts` | `UNIQUE(losing_log_id)` | upsert idempotent d'un conflit |
| `scan_conflicts` | `(event_id, status, detected_at DESC)` | `GET /conflicts?status=` |
| `scan_conflicts` | `(ticket_id, station)` | mise à jour des conflits quand le gagnant change |
| `checkin_entitlements` | `(event_id, version, ticket_id)` | snapshot delta `version > $since` + curseur |
| `checkin_terminals` | `(event_id, last_seen_at DESC)` | `/stats` par terminal |

Chaque index coûte une écriture : à 300 scans/min c'est négligeable, mais **seuls les index de
ce tableau sont créés**, et TDEV-56 vérifie chacun par `EXPLAIN (ANALYZE, BUFFERS)` (`PERF.md`).
À 20 000 lignes, un scan séquentiel reste rapide : les index « optionnels » seront retirés s'ils ne servent pas.

### 1.8 Synchronisation avec `admissions` (3A) — **volontairement non faite**

Aucune écriture dans `admissions` (règle 5). Risque à connaître : un même billet pourrait être
admis une fois par `POST /api/scan` (3A) **et** une fois par `/api/checkin/scan`, sans que les deux
systèmes le sachent. Mitigation documentée : les terminaux 3B n'utilisent que `/api/checkin/*`.
Décision à prendre par Trésor : voir `OPEN_QUESTIONS.md` (Trésor, Q1).

---

## 2. Contrat d'API (préfixe `/api/checkin`, OpenAPI généré par FastAPI)

Erreurs : même enveloppe que le 3A (`http_layer/errors.py`) :
`{"error": {"code": "<snake_case>", "message": "<texte humain>"}}`. Jamais de QR, jeton ni donnée personnelle dans `message`.

### 2.1 `GET /snapshot?event_id=&since_version=&cursor=&limit=`
Rôle `scanner`+. Droits par billet pour le cache offline.
- Sans `since_version` : snapshot complet ; avec : **delta** (`version > since_version`).
- `ETag: "<event_id>:<max_version>:<rules_hash>"` ; `If-None-Match` → `304`. `Content-Encoding: gzip`
  (octets compressés **mis en cache** par (événement, version), jamais recompressés à chaque terminal).
- Pagination par curseur (`limit` défaut 2 000, max 5 000) épinglée sur `snapshot_version` pour qu'une
  page 2 ne mélange pas deux versions.
- Rafraîchissement : si `now - refreshed_at > CHECKIN_SNAPSHOT_TTL_SECONDS` (défaut 15 s), **un seul** processus recalcule
  (`pg_try_advisory_xact_lock`), compare `content_hash` et ne ré-attribue une `version` qu'aux lignes modifiées.

```json
{
  "event_id": "01J8ZK8T0M8N0P0Q0R0S0T0U0E",
  "snapshot_version": 4812,
  "since_version": 4700,
  "generated_at": "2026-10-03T08:00:05Z",
  "has_more": false,
  "next_cursor": null,
  "issuer_keys": { "k_If4x36FUomFia_hUBG_SJw": "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo" },
  "entitlements": [
    {
      "ticket_id": "01J8ZK8T0M8N0P0Q0R0S0T0U0V",
      "serial": "TDEV-2026-0042",
      "ticket_type_id": "01J8ZK8T0M8N0P0Q0R0S0T0U0T",
      "status": "valid",
      "stations": ["EVENT_ENTRY"],
      "uses": { "EVENT_ENTRY": 1 },
      "version": 4805
    }
  ]
}
```
Clés publiques : via les fonctions **du 3A** (`events/issue.issuer_public_keys`, `tickets/capability.key_id`),
appelées sur une connexion de mon pool enveloppée dans un `Store` *en lecture seule*. La crypto n'est jamais réécrite.
Aucun nom/e-mail de participant dans le snapshot (minimisation) : le terminal n'en a pas besoin pour décider.

### 2.2 `POST /scan` — scan **en ligne** unitaire
Rôle `scanner`+.
```json
{ "event_id": "01J8…E", "terminal_id": "7d0c6c1e-2b7e-4f0e-9a51-6f0f4e2f6a11",
  "station": "EVENT_ENTRY", "capability": "chantier3a.<payload>.<sig>",
  "operation_id": "b1c2…", "scanned_at": "2026-10-03T08:01:02Z" }
```
1. Vérifie la capability avec `tickets/capability.verify_with_ring` (+ `peek_eid`) et les clés de l'événement.
2. Applique la règle du poste, **consomme** (ou constate l'épuisement) dans une transaction avec verrou (§3.5), journalise.
3. Répond (cible p95 < 200 ms) :
```json
{ "status": "accepted", "server_decision": "valid", "reason": "",
  "ticket_id": "01J8…V", "serial": "TDEV-2026-0042", "station": "EVENT_ENTRY",
  "use_index": 0, "first_scanned_at": null, "operation_id": "b1c2…" }
```
Doublon en ligne : `server_decision: "already_scanned"`, `first_scanned_at` renseigné, `status: "accepted"` (le refus est le
résultat nominal : personne n'est entré, donc aucun conflit). Un scan en ligne n'est un « prétendant » (`is_claim`) que s'il a été
répondu `valid`. `operation_id` est optionnel pour l'app (généré côté serveur sinon) mais
**recommandé** pour rejouer une requête sans double consommation. Le QR brut n'est jamais persisté ni journalisé.

### 2.3 `POST /sync` — lot hors ligne
Rôle `scanner`+. Taille max configurable (`CHECKIN_SYNC_MAX_BATCH`, défaut 500 ; lot recommandé : 200).
```json
{
  "event_id": "01J8…E",
  "terminal_id": "7d0c6c1e-2b7e-4f0e-9a51-6f0f4e2f6a11",
  "batch_id": "0a9d…",
  "device_sent_at": "2026-10-03T08:15:00Z",
  "app_version": "0.3.1+12",
  "operations": [
    { "operation_id": "b1c2…", "scan_id": "e5f6…", "ticket_id": "01J8…V", "participant_id": null,
      "station": "eventEntry", "decision": "valid",
      "evaluated_at": "2026-10-03T08:01:02Z", "previous_scan_at": null,
      "qr_version": 1, "staff_id": null, "capability": null }
  ]
}
```
Champs **déjà** dans l'outbox 3B : `operation_id, scan_id, ticket_id, participant_id, station, decision, evaluated_at, previous_scan_at`.
Champs **à ajouter par Rodrigue** : `event_id`, `terminal_id`, `batch_id`, `device_sent_at`, `app_version`, `qr_version`;
**recommandés** : `staff_id` (par défaut, l'utilisateur authentifié — faux si l'équipe change entre le scan et la synchro) et
`capability` (sans elle, le serveur ne peut pas re-vérifier la signature : `capability_verified = NULL`, voir Daniel Q3 ; jamais stockée).

Réponse **partielle** `200`, un statut par `operation_id`, dans l'ordre reçu :
```json
{
  "batch_id": "0a9d…", "received_at": "2026-10-03T08:15:00.412Z", "clock_offset_ms": 412,
  "summary": { "accepted": 197, "already_processed": 1, "conflict": 1, "rejected": 1 },
  "results": [
    { "operation_id": "b1c2…", "status": "accepted", "server_decision": "valid", "conflict": null },
    { "operation_id": "c3d4…", "status": "already_processed", "server_decision": "valid", "conflict": null },
    { "operation_id": "d5e6…", "status": "conflict", "server_decision": "already_scanned",
      "conflict": { "type": "CROSS_TERMINAL_DOUBLE_ADMISSION", "winning_terminal_id": "3f2a…", "winning_at": "2026-10-03T08:01:00Z" } },
    { "operation_id": "e7f8…", "status": "rejected", "error_code": "unknown_station", "message": "station 'xyz' is not configured" }
  ]
}
```
Statuts : `accepted` (journalisé) · `already_processed` (rejeu : renvoie le résultat **d'origine**, rien n'est écrit) ·
`conflict` (journalisé, mais pas gagnant ou inéligible) · `rejected` (non journalisé, code stable).
Une opération mal formée n'invalide **jamais** le lot. Les erreurs d'infrastructure (base, verrou) renvoient `503` + `Retry-After`
pour **tout** le lot : le rejeu est sans danger (idempotence). Un `operation_id` déjà connu avec un **contenu différent**
(`payload_hash`) est `rejected` / `operation_id_reuse`.

### 2.4 `GET /conflicts?event_id=&status=&type=&cursor=&limit=` · `POST /conflicts/{id}/acknowledge`
Rôle `admin`+ (superviseur). `acknowledge` : `{ "note": "…" }` → `status: acknowledged`, `resolved_by`, `resolved_at`. Idempotent.
```json
{ "conflicts": [ { "conflict_id": 12, "type": "CROSS_TERMINAL_DOUBLE_ADMISSION", "station": "EVENT_ENTRY", "ticket_id": "01J8…V",
  "serial": "TDEV-2026-0042", "clock_suspect": false, "status": "open", "detected_at": "2026-10-03T08:15:00Z",
  "winning": { "log_id": 901, "terminal_id": "3f2a…", "corrected_evaluated_at": "2026-10-03T08:01:00Z" },
  "losing":  { "log_id": 955, "terminal_id": "7d0c…", "corrected_evaluated_at": "2026-10-03T08:01:02Z" } } ],
  "next_cursor": null }
```

### 2.5 `GET /logs?event_id=&station=&ticket_id=&terminal_id=&since=&cursor=&limit=`
Rôle `admin`+ (contient des identifiants d'agents). Pagination par curseur `log_id` (défaut 200, max 1 000). Jamais de capability dans la réponse.

### 2.6 `GET /stats?event_id=`
Rôle `scanner`+ (compteurs seulement, pas de données personnelles).
```json
{ "event_id": "01J8…E", "as_of": "2026-10-03T08:20:00Z",
  "by_station": { "EVENT_ENTRY": { "valid": 2310, "already_scanned": 41, "not_authorized": 3, "invalid": 7 } },
  "conflicts": { "open": 2, "acknowledged": 0, "by_type": { "CROSS_TERMINAL_DOUBLE_ADMISSION": 2 } },
  "terminals": [ { "terminal_id": "7d0c…", "label": "Porte A", "last_seen_at": "2026-10-03T08:19:40Z",
                   "clock_offset_ms": 412, "revoked": false, "last_batch_at": "2026-10-03T08:15:00Z" } ] }
```
« File en attente par terminal » : **le serveur ne voit pas l'outbox locale**. Il fournit `last_seen_at` / `last_batch_at` ;
l'app devrait envoyer son nombre d'opérations en attente (`pending_count`) dans l'enveloppe de `/sync` (proposition à Rodrigue).

### 2.7 `GET /health`
Sans authentification, sans donnée sensible : `{"status":"ok","db":"ok","pool":{"size":8,"available":6,"waiting":0}}` ; `503` si la base ne répond pas en < 1 s.

### 2.8 Décisions : correspondance et codes

Décisions serveur (`server_decision`, snake_case) :
`valid · already_scanned · not_authorized · invalid · expired · not_yet_valid · unknown · wrong_event · revoked`.

| Décision 3B (`reported_decision`, verbatim) | Normalisée | Décision serveur attendue (cas nominal) |
|---|---|---|
| `valid` | `valid` | `valid` (ou `already_scanned` / `not_authorized` / `revoked` si le serveur en décide autrement) |
| `alreadyScanned` / `ALREADY_SCANNED` | `already_scanned` | `already_scanned` |
| `invalid` / `INVALID` | `invalid` | `invalid`, `wrong_event` ou `revoked` |
| `notAuthorized` / `NOT_AUTHORIZED` | `not_authorized` | `not_authorized` |
| `expired` / `EXPIRED` | `expired` | `expired` ou `not_yet_valid` |
| `unknown` / `UNKNOWN` | `unknown` | `unknown` |
| autre valeur | — | `rejected` / `invalid_decision` |

| Résultat 3A (`POST /api/scan`) | `server_decision` équivalente |
|---|---|
| `admitted` | `valid` |
| `duplicate` | `already_scanned` |
| `invalid` (`reason` : `bad_signature`, `malformed`, `unsupported_version`, `unknown_kid`) | `invalid` |
| `invalid` (`expired`) / (`not_yet_valid`) | `expired` / `not_yet_valid` |
| `invalid` (« ticket revoked or not valid ») | `revoked` |
| `wrong_event` | `wrong_event` |
| — (pas de billet) | `unknown` · — (poste non autorisé) | `not_authorized` |

Postes : `eventEntry`/`EVENT_ENTRY`, `foodAccess`/`FOOD_ACCESS`, `merchPickup`/`MERCH_PICKUP`,
`afterEntry`/`AFTER_ENTRY` → forme canonique `UPPER_SNAKE`.
**Seul** un `reported_valid` + éligibilité serveur rend une opération « prétendante » (`is_claim`). Une décision `alreadyScanned`/`invalid`… du terminal est de la **preuve d'audit**, pas une consommation.

Codes d'erreur stables (snake_case) :
`invalid_request` · `unauthorized` · `forbidden` · `rate_limited` · `event_not_found` · `terminal_revoked` ·
`terminal_event_mismatch` · `batch_empty` · `batch_too_large` · `operation_invalid` · `operation_id_reuse` ·
`unknown_station` · `invalid_decision` · `unsupported_qr_version` · `ticket_not_found` · `signature_invalid` ·
`service_busy` (503) · `internal_error`.

### 2.9 Limitation de débit
Limiteur par terminal (et par IP) interne au module, configurable (`CHECKIN_RATE_LIMIT_PER_TERMINAL`, défaut : 600/min) — le limiteur 3A ne couvre pas `/api/checkin`. Les IP de salle sont probablement partagées (NAT) : **ne pas limiter par IP seule** [SUPPOSÉ].

---

## 3. Résolution de conflits (TDEV-55)

Détail, pseudo-code et justification : **`ADR-001-conflits.md`**. Résumé :

- **État dérivé** : pour un (ticket, station), l'ensemble des prétendants (`scan_logs.is_claim`) est trié par la clé
  `(clock_suspect, corrected_evaluated_at, operation_id)` ; les `max_uses` premiers détiennent `use_index 0..max_uses-1`.
  L'état est une **fonction de l'ensemble** des logs ⇒ indépendant de l'ordre d'arrivée, idempotent, convergent.
- **Correction d'horloge par lot**, pas lissée par terminal : `clock_offset = server_received_at − device_sent_at` du lot,
  figé dans chaque log. *Je m'écarte de la proposition « lissé par terminal »* : un offset lissé dépend de l'historique des
  lots, donc de leur ordre d'arrivée, ce qui casse la convergence. Le lissage reste un indicateur de diagnostic (`checkin_terminals`).
- **Verrou** : `pg_advisory_xact_lock(hashtextextended(ticket_id || ':' || station, 0))`, acquis dans l'ordre trié des clés (évite les deadlocks).
- **Types** : `CROSS_TERMINAL_DOUBLE_ADMISSION`, `SAME_TERMINAL_REPLAY`, `LATE_REVOKED`, `NOT_AUTHORIZED_SERVER_SIDE`, `CLOCK_SUSPECT`.

---

## 4. Performance (TDEV-56)

### 4.1 Hypothèses de charge (**suppositions, pas des données du projet** ; configurables, à faire confirmer)
3 000 participants · 10 terminaux · pic 300 scans/min (5/s) à l'ouverture · lots de 200 opérations après une coupure réseau de 15 min
(rafale : 10 terminaux × 200 ≈ 2 000 opérations en quelques secondes). Cibles à confirmer : `/scan` p95 < 200 ms ; lot de 200 < 2 s.

### 4.2 Pool et modèle de concurrence
- `psycopg_pool.ConnectionPool` **dédié** (par processus), séparé de la connexion unique du `Store` 3A. Taille : min 2, max 10 (`CHECKIN_DB_POOL_MIN/MAX`).
- Endpoints en `def` (pas `async`) : le pool sync `psycopg_pool.ConnectionPool` + les fonctions 3A synchrones (`Store`, `validate_session`, `issuer_public_keys`) sont réutilisés tels quels ; FastAPI les exécute dans son *threadpool* (40 threads par défaut ≥ taille du pool). Un `async` avec `AsyncConnectionPool` ne pourrait pas réutiliser les fonctions 3A sans bloquer la boucle. À revoir **si** le profilage montre une saturation du threadpool.
- `psycopg-pool` est déjà dans le venv mais **absent de `pyproject.toml`** : je l'y ajoute (modification autorisée).

### 4.3 Écritures
- Insertion en lot : `INSERT INTO scan_logs (...) SELECT ... FROM unnest($1::uuid[], $2::text[], …) ON CONFLICT (operation_id) DO NOTHING RETURNING operation_id, log_id` — **pas de `try/except` sur l'unicité**, un seul aller-retour.
  (`COPY` est plus rapide en volume mais ne supporte pas `ON CONFLICT` ; inutile à 200 lignes.)
- **Une transaction par lot** (pas par groupe) : les verrous sont pris dans l'ordre trié, ce qui exclut les deadlocks ; la durée de détention reste de l'ordre de la
  dizaine de millisecondes pour 200 opérations. Une transaction par groupe (ticket, station) ajouterait ~200 `COMMIT`/`fsync` par lot. Si le profilage montre des attentes de verrou, repli : sous-lots de 50.
- `SET LOCAL lock_timeout = '2s'` ; dépassement → `503 service_busy` + `Retry-After`.

### 4.4 Lectures
Pas de N+1 : un lot charge en **3 requêtes** les billets concernés (`= ANY($1)`), les règles de l'événement, et les consommations/prétendants existants des groupes touchés.

### 4.5 Snapshot
Pré-calculé (`checkin_entitlements`), versionné, ETag, gzip mis en cache (§2.1) ; rafraîchi au plus toutes les 15 s par un seul processus.

### 4.6 Déploiement : workers et mode autonome
- `billetterie-api serve` lance `uvicorn.run(app)` **sans workers** (`cli.py`) : inchangé.
- Le module expose `checkin.asgi:app` (**application autonome** : routeur check-in + authentification `TerminalAuth`, **sans** le `session_middleware` du 3A) :
  `uvicorn checkin.asgi:app --workers 4`. Le pool est **par processus** : connexions totales = `workers × CHECKIN_DB_POOL_MAX` (≤ `max_connections` − connexions du 3A).
- En mode **monté** (router ajouté à `http_layer/app.py`, comme demandé) le module hérite du middleware 3A : il dépend de la correction du bug 2 (`BUGS_3A.md`). Je recommande le mode autonome pour le Jour J, sans changer le code : même module, deux points d'entrée.
  (Sous Windows, `gunicorn` n'existe pas : `uvicorn --workers` suffit.)

### 4.7 Mesure
Locust dans `backend/tests/load/` (scans en ligne + rafales de synchro) ; `docs/checkin/PERF.md` : p50/p95/p99, débit, erreurs, **avant/après** (référence « avant » = version naïve : connexion unique, `try/except`, lot ligne par ligne), plans `EXPLAIN (ANALYZE, BUFFERS)` de chaque requête chaude.
Locust n'est pas installé : je l'ajouterai dans le venv (dépendance `dev`) au moment de TDEV-56, après accord.

---

## 5. Authentification des terminaux

- **Port** `TerminalAuth` (`checkin/ports.py`) : `authenticate(request) -> Principal(user_id, scopes, terminal_id?)`. Adaptateur par défaut `Sessions3AAuth` :
  extrait le jeton avec `http_layer.session.extract_token`, valide la session avec `auth.service.validate_session` et le droit avec
  `auth.rbac.can_manage_event(…, ROLE_SCANNER | ROLE_ADMIN)`, **sur une connexion de mon pool** (et non la connexion partagée du `Store` 3A).
  La session Staff d'Amélie se branchera en écrivant un second adaptateur, sans toucher au reste.
- Rôles : `scanner` → `/scan`, `/sync`, `/snapshot`, `/stats` ; `admin` → `/conflicts`, `/acknowledge`, `/logs`.
- **Enregistrement au premier appel** : `INSERT … ON CONFLICT (terminal_id) DO UPDATE SET last_seen_at = now()`. Un `terminal_id` déjà rattaché à **un autre événement** → `403 terminal_event_mismatch`.
- **Révocation** : `revoked_at` non nul ⇒ tout nouveau lot/scan est refusé `403 terminal_revoked` ; les scans déjà journalisés restent intacts.
  Conséquence à connaître : les scans faits hors ligne *avant* la révocation mais non encore synchronisés sont refusés aussi (défaut prudent) → question à Abdoul-Rachid.
  Pas d'endpoint de révocation dans ce périmètre (SQL documenté) sauf demande.
- CSRF : les mobiles utilisent `Authorization: Bearer` (pas de CSRF) ; en mode monté, le middleware 3A traite le CSRF des sessions par cookie.

---

## 6. Plan de tests (Phase 2, rappel)

PostgreSQL réel (`TEST_DATABASE_URL`, refus de tourner si le nom de base ne finit pas par `_test`), `backend/tests/checkin/`.
`domain.py` : fonctions pures testées sans base (y compris **permutations d'ordre d'arrivée** → même gagnant). Liste complète des cas : énoncé de mission §Phase 2 (TDEV-54 puis TDEV-55), plus : `operation_id_reuse`, snapshot delta/ETag, `/health`, rôles.

## 7. Extensibilité (sans coder l'« API centrale »)

Ports/adaptateurs : `TerminalAuth` (session), `TicketSource` (lecture billets/règles/clés : adaptateur 3A en SQL sur la même base ; adaptateur « fichier snapshot JSON » = plan de repli CIBLE B),
`Clock` (tests). Contrats versionnés : préfixe `/api/checkin`, champ `qr_version` accepté (seule la valeur 1 est supportée, sinon `unsupported_qr_version`), `schema_version` dans les réponses
de `/snapshot`. Ce qu'il faudrait savoir pour une API centrale : `OPEN_QUESTIONS.md` § « API centrale ».
