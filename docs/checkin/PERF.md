# Performance de l'API de check-in (TDEV-56)

Mesures du 2026-09-30, branche `feat/checkin`. Outils et commandes : [`backend/tests/load/README.md`](../../backend/tests/load/README.md).

**Lisez d'abord les limites (§9).** Ce sont des mesures sur un PC de développement (Windows, tout sur la même machine) avec
**des hypothèses de charge, pas des données du projet**. Elles disent si l'architecture tient et où sont les goulots ;
elles ne remplacent pas une simulation Jour J sur le matériel réel (Abdoul-Rachid).

## 1. Verdict

| Cible (à confirmer) | Résultat | |
|---|---|---|
| `/scan` p95 < 200 ms à la charge nominale (10 terminaux, ~300 scans/min) | **73 à 119 ms** (p99 164 à 195 ms), 0 erreur | ✅ |
| Lot de 200 opérations synchronisé en < 2 s | **134 à 146 ms** seul ; **p95 0,37 à 0,98 s** quand 10 terminaux envoient leur lot **en même temps** (2 000 opérations) | ✅ |
| `/scan` p95 < 200 ms **pendant** une rafale de synchro (10 terminaux qui scannent + 10 qui envoient un lot toutes les 3 s) | **698 ms avec 1 processus**, **216 ms avec 4 processus** (p99 347 ms) | ⚠️ ≥ 2 processus nécessaires, et encore juste |
| Pas de perte, pas de double consommation | 0 échec sur toutes les mesures ; tests de convergence et de concurrence verts | ✅ |

Conclusion : à la charge supposée, **un seul processus suffit largement** pour les scans en ligne (marge ×15 : il sature vers 70 à 90 scans/s
pour 5 scans/s attendus). Ce qui le met en difficulté est la **synchro en rafale**, qui occupe le processus. Déployer **plusieurs processus**
(voir §8 : pas `--workers` sous Windows) règle le problème.

## 2. Conditions de mesure

- Machine : Windows 11, 8 cœurs logiques. Python 3.12.9, FastAPI 0.141, uvicorn 0.54, psycopg 3.3.6.
- Base : PostgreSQL 16.15 dans Docker Desktop, **`fsync` actif**, volume disque réel (`tdev-checkin-perf-pg`). (Les tests unitaires utilisent une base en `tmpfs` sans `fsync` : trop optimiste pour des temps d'écriture.)
- Données : 1 événement, **3 000 billets** signés (2 400 « GA », 600 « VIP ») créés par l'API 3A ; règles de postes pour `FOOD_ACCESS`, `AFTER_ENTRY`, `MERCH_PICKUP`.
- Générateur de charge : `tests/load/loadgen.py` (Python, `httpx` + threads), **sur la même machine** que le service et la base. Il consomme du CPU
  pris au service : les chiffres sont donc plutôt **pessimistes**. Locust n'a pas pu être utilisé (§9).
- Service : `checkin.asgi:app` (mode autonome), pool de 2 à 10 connexions par processus, **un run par cellule** (pas de répétition statistique) :
  compter ±15 % de bruit, plus pour les p99 (peu d'échantillons).
- Scénarios :
  - **nominal** : 10 terminaux × 1 scan toutes les 1,5 à 2,5 s (≈ 300/min) + 1 terminal qui envoie un lot de 200 toutes les 15 s, 10 % de doublons, 40 s ;
  - **saturation** : 30 terminaux qui enchaînent les scans (boucle fermée), 30 s ;
  - **rafale** : 10 terminaux envoient **chacun un lot de 200 en même temps** (2 000 opérations) ;
  - **rafale mixte** : 10 terminaux qui scannent + 10 qui envoient un lot de 200 toutes les 3 s, 30 s.

## 3. Avant / après

« Avant » = le code de TDEV-55 (commit `8345cae`), « après » = le code final de TDEV-56, **même machine, mêmes scénarios**. Latences en ms.

| Scénario | Avant (1 proc.) | + micro-optimisations seules | Après (1 proc.) | Après (4 proc.) |
|---|---|---|---|---|
| **Nominal** — scan p50 / p95 / p99 | 63,8 / 113,8 / 199,1 | 58,0 / 108,1 / 283,1 | 57,4 / 119,4 / 195,0 | **48,8 / 73,2 / 163,5** |
| **Nominal** — lot de 200, p50 | 417,9 | 400,8 | **145,5** | **134,2** |
| **Saturation** — débit · scan p50 / p95 | 92 req/s · 270 / 328 | 76 req/s · 334 / 422 | 70 req/s · 369 / 451 | **237 req/s** · 91 / 132 |
| **Rafale 10 × 200** — p50 / p95 | 1 329 / **2 384** | 1 413 / 2 749 | 724 / 983 | **273 / 368** |
| **Rafale mixte** — scan p50 / p95 / p99 | 84,0 / 579,7 / 655,7 | 87,6 / 480,2 / 1 504 | 69,5 / 697,8 / 795,4 | **49,7 / 215,9 / 346,9** |
| **Rafale mixte** — lot de 200 p50 / p95 | 2 005 / **2 587** | 1 944 / 2 556 | 337 / 764 | **283 / 439** |

« 4 proc. » = 4 processus uvicorn à 1 worker chacun (ports 8090 à 8093), clients répartis en tourniquet : ce que ferait un proxy inverse (§8).
Erreurs : 0 sur toutes les cellules.

### Ce qui a vraiment fait la différence, et ce qui n'a rien changé

| Changement | Effet mesuré |
|---|---|
| **Écrire les résolutions d'un lot avec 2 requêtes au lieu de ~400** (`sync_service.py`, `resolution_rows`) | **lot de 200 : 430 → ~120 ms** (profil mono-thread) ; p95 en rafale 2 384 → 983 ms. **C'est le vrai gain** : le profil montrait 1,5 s sur 2 s passées à appeler `upsert_*` groupe par groupe (N+1 en écriture). |
| Insertion en lot (`unnest` + `ON CONFLICT DO NOTHING`) au lieu d'une ligne + un `COMMIT` | micro-mesure 200 opérations : **966 → 29 ms (×33)**, voir §4 |
| Plusieurs processus | **débit ×2,6 à ×3,4**, p95 scan en rafale mixte 698 → 216 ms |
| Réécriture du rafraîchissement du snapshot (jointures au lieu de sous-requêtes par billet) | **540 → 121 ms** pour recalculer 3 000 billets (§5) |
| `register_terminal` sans écriture à chaque scan, cache des clés (30 s), pas de pré-contrôle de rejeu sans `operation_id`, cache de `/stats` (2 s) | **aucun gain mesurable sur le débit ni la latence** (colonne « micro-optimisations seules » : dans le bruit). Ils retirent un `COMMIT` et ~4 allers-retours SQL par scan ; je les garde parce qu'ils réduisent la charge sur la base, **pas** parce que les chiffres les prouvent. |
| Cache d'authentification (`CHECKIN_AUTH_CACHE_SECONDS`) | implémenté mais **désactivé par défaut** et non mesuré en charge : une session fermée resterait valable jusqu'à ce délai (compromis sécurité à valider avec Abdoul-Rachid). |

Profil d'un scan (mono-thread, base réelle) : 19,7 ms, dont **76 % d'attente de la base** (13 requêtes SQL). Le processus n'est pas saturé par le calcul ;
en charge, la saturation d'un processus (≈ 70 à 90 scans/s) vient du cumul FastAPI + JSON + SQL sous le GIL. Pour un gain supplémentaire il faudrait
**moins d'allers-retours** (par ex. une fonction SQL unique qui fait contrôle + consommation + journal) : non fait, le besoin n'est pas là.

## 4. Écritures : ligne par ligne contre en lot

`tests/load/bench_bulk.py`, 200 opérations, 30 exécutions après 3 de chauffe, base avec `fsync` :

| | p50 | p95 | max |
|---|---:|---:|---:|
| naïf : 1 `INSERT` + `COMMIT` par opération, 1 `SELECT` par billet, `try/except` sur l'unicité | 966 ms | 1 027 ms | 1 135 ms |
| module : 1 requête pour les billets + 1 `INSERT … ON CONFLICT DO NOTHING` | **29 ms** | 35 ms | 36 ms |

Le coût du naïf est presque entièrement le `COMMIT`/`fsync` répété (≈ 4,8 ms par opération).

## 5. Plans `EXPLAIN (ANALYZE, BUFFERS)`

`tests/load/explain.py` appelle les **vraies fonctions** de `repository.py` via un proxy qui passe chaque requête en `EXPLAIN ANALYZE`.
Base gonflée à **200 000 lignes de journal** (la charge attendue est ~20 000) ; tout est annulé après coup. Lot simulé : 200 opérations.

| Requête | Exécution (ms) | Index utilisé |
|---|---:|---|
| `load_tickets` (200 ids, 1 requête) | 0,83 | `tickets_pkey` |
| `load_rules` | 0,06 | `checkin_station_rules_pkey` |
| `find_operations` (rejeu, 200 ids) | 0,57 | `scan_logs_operation_id_key` |
| **`fetch_claims` (200 couples billet/poste)** — chemin critique | **2,65** | **`idx_scan_logs_claims`** (index partiel `WHERE is_claim`) |
| `insert_logs` (200 lignes, `ON CONFLICT DO NOTHING`) | 10,25 | — |
| `upsert_consumptions` (200 lignes) | 20,95 | clé primaire |
| `upsert_conflicts` (200 lignes) | 14,30 | `UNIQUE(losing_log_id)` |
| `list_logs` (page de 200, curseur) | 0,18 | `scan_logs_pkey` |
| `list_logs` filtre `terminal_id` | 0,58 | `idx_scan_logs_terminal` |
| `list_logs` filtre `ticket_id` | 17,84 | **aucun : balayage séquentiel** |
| `list_conflicts` (ouverts, plus récents d'abord) | 1,03 | `idx_scan_conflicts_event_status` |
| `stats` — agrégat des décisions | 46,94 | **aucun : balayage séquentiel** |
| `stats` — consommations / conflits / terminaux | 0,16 / 0,22 / 0,14 | index dédiés |
| rafraîchissement du snapshot (recalcul de 3 000 billets) | **121,38** (avant réécriture : **539,51**) | clés primaires ; jointures |
| `snapshot_page` (delta, 2 000 lignes) | 0,79 | `idx_checkin_entitlements_delta` |

Tout le **chemin d'écriture d'un scan ou d'un lot** utilise ses index et coûte au total de l'ordre de 35 à 50 ms pour 200 opérations côté base.
Les plans complets sont régénérables avec la commande du README (ils dépendent des données).

### Deux balayages séquentiels laissés volontairement

J'ai testé les deux index qui les supprimeraient (`(ticket_id, log_id)` et `(event_id, station, server_decision)`) : ils **coûtent ~15 % d'écriture**
(insertion de 200 opérations : p50 31 → 36 ms, p95 38 → 62 ms) pour des lectures **rares** ou **cachables** :

- `/logs?ticket_id=` est une requête de superviseur : 18 ms à 200 000 lignes (≈ 2 ms à la taille attendue). Pas d'index.
- `/stats` : 47 ms à 200 000 lignes (≈ 5 ms attendu) ; déjà protégé par un **cache de 2 s** par événement, donc au plus une exécution toutes les 2 s quel que soit le nombre de tableaux de bord.

À reconsidérer si le journal dépasse ~1 M de lignes.

## 6. Snapshot

- Recalcul complet de 3 000 billets : ~120 ms, **au plus une fois toutes les 15 s** par événement et par un seul processus (`pg_try_advisory_xact_lock`) : < 1 % d'un cœur.
- Si rien n'a changé, aucune `version` n'est réattribuée (vérifié) : les terminaux en mode delta ne téléchargent rien.
- Le corps est sérialisé et compressé (gzip) **une seule fois** par (événement, version, page), puis servi depuis la mémoire du processus ; `ETag` → `304`.

## 7. Les deux bugs du 3A qui apparaissent en charge

Mesurés sur l'endpoint **existant** `POST /api/scan` (application 3A seule, 1 processus) avec le même générateur :

| Scénario | Résultat |
|---|---|
| nominal, aucun doublon, limiteur désactivé | p50 37,6 / p95 80,1 ms, 0 erreur : **le chemin simple est rapide** (il fait moins : pas de journal des refus, pas de règles par poste) |
| nominal, **10 % de doublons** | **192 requêtes sur 196 en HTTP 500** : après le premier doublon la connexion unique est bloquée (bug 2) |
| saturation, billets épuisés au bout de ~1 800 scans | 272 × HTTP 500 + 13 erreurs de lecture, même cause ; 69 req/s |
| nominal **tel que livré** (limiteur actif) | **38 % des requêtes rejetées (429)** : le limiteur `ScanRateLimitMiddleware` est à 120 requêtes/min **par IP**, or 300 scans/min depuis un même site (probablement une seule IP par NAT) le dépassent largement |

Le module check-in a ses propres limiteurs (par terminal) et son propre pool : il n'a aucun de ces deux défauts.
(Pour les mesures du 3A seul, `tests/load/legacy_app.py` peut lever le limiteur — `LEGACY_DISABLE_RATE_LIMIT=1` — sans modifier le code 3A.)

## 8. ⚠️ Plusieurs workers : pas `uvicorn --workers` sous Windows

Avec `uvicorn checkin.asgi:app --workers 4` **sous Windows**, des requêtes restent bloquées **15 s ou 30 s** (1 à 6 requêtes sur ~190 par run ; **10 des 12 runs nominaux** à 4 workers).
Cause établie avec des preuves :

- Côté serveur, la **boucle d'événements d'un worker a été gelée 15,08 s** (mesure de retard de boucle) et les deux requêtes en cours dans ce worker ont duré 15,3 s.
- Le cliché des piles (`faulthandler`, prélevé par un thread C, donc possible pendant le gel) montre le thread principal du worker **bloqué dans `socket.accept()`**
  (`asyncio/selector_events.py:_accept_connection`).
- Mécanisme (hypothèse cohérente avec ces preuves) : le socket d'écoute partagé entre les processus est en mode bloquant ; quand plusieurs workers sont
  réveillés par la même connexion entrante, les perdants restent bloqués dans `accept()` jusqu'à l'arrivée de la **connexion suivante**
  (ici toutes les ~15 s : le terminal de synchro se reconnecte après l'expiration du keep-alive).
- Écartés par mesure : la base (aucune session bloquée, `pg_stat_activity`), la création de connexions (2 696 connexions, p99 91 ms), `/health` avec 4 workers (aucun gel).
- Ce n'est **pas** un défaut du module : aucun thread n'était dans son code pendant le gel. **Non testé sous Linux** (où les workers partagent le socket autrement) — à vérifier en déploiement cible.

**Recommandation** : en production Linux, `--workers N` est la voie normale (à valider) ; sur Windows, ou par prudence, lancer **N processus à 1 worker** sur
des ports différents derrière un proxy inverse (nginx, Caddy, HAProxy…). C'est ce qui a été mesuré dans la colonne « 4 proc. ». Le `/health` d'un processus ne prouve
que lui-même : attendre que **tous** aient ouvert leur pool avant d'ouvrir le trafic. Connexions à la base = processus × `CHECKIN_DB_POOL_MAX`.

## 9. Limites de ces mesures — ce qui n'est pas démontré

- **Hypothèses de charge** (3 000 participants, 10 terminaux, 300 scans/min, lots de 200) : des suppositions, à confirmer (Romain, Abdoul-Rachid).
- **Une machine** : service, base et générateur se partagent 8 cœurs et un disque. Pas de latence réseau 4G/wifi, pas le matériel de la salle.
- **Un run par cellule**, pas de répétition : ±15 % de bruit ; p99 et « max » reposent sur peu d'échantillons (n de 90 à 230 par run nominal).
- **Locust non exécuté** : une stratégie de contrôle d'application de Windows bloque la bibliothèque native de `gevent` (`_gevent_c_greenlet_primitives`) sur cette machine ;
  je n'ai pas contourné cette protection. `locustfile.py` est fourni mais **non testé ici**. Toutes les mesures viennent de `loadgen.py`, dont les scénarios sont les mêmes.
- **Linux** et **`--workers` sous Linux** non mesurés (§8).
- Les billets de la rafale sont réutilisés en boucle (le lot cyclique produit de vrais conflits) : le chemin de conflit est donc inclus dans les temps de synchro.
- Le cache de clés (30 s) signifie qu'une clé révoquée reste acceptée jusqu'à 30 s dans un processus ; le cache d'authentification, s'il est activé, garde une session fermée valable jusqu'à son délai.
- Limite de capacité du **3A**, hors de ce module : la référence publique `TDEV-YYYY-NNNN` n'a que 4 chiffres (≈ 10 000 billets par an) et des commandes de plusieurs billets
  peuvent tirer deux fois le même numéro (voir `BUGS_3A.md`, observation 4).

## 10. Reproduire

```bash
cd backend
# base réaliste + jeu de données + service(s) + charge : voir tests/load/README.md
python tests/load/bench_bulk.py --ops 200 --runs 30
python tests/load/explain.py --scale 200000 > explain.md
python tests/load/loadgen.py --scenario checkin --host http://127.0.0.1:8090 --users 10 --syncers 1 --duration 45
```
