# Bugs constatés dans le 3A (à traiter par Trésor)

Constatés le 2026-09-30 sur `main` (commit `208f0b6`), avec PostgreSQL 16 (Docker) et
psycopg 3.3.6, Python 3.12.9. **Le module check-in ne corrige aucun de ces points**
(règle : ne pas modifier le comportement existant du 3A). Chacun est reproductible ci-dessous.

Préparation commune (base jetable, jamais une vraie base : `conftest.py` fait un `TRUNCATE`
de toutes les tables publiques) :

```bash
docker run -d --name pg-test -p 127.0.0.1:5433:5432 \
  -e POSTGRES_USER=checkin_test -e POSTGRES_PASSWORD=checkin_test \
  -e POSTGRES_DB=chantier3a_test postgres:16-alpine
export TEST_DATABASE_URL="postgresql://checkin_test:checkin_test@127.0.0.1:5433/chantier3a_test?sslmode=disable"
```

## Bug 1 — `migrate_postgres()` n'enregistre rien (`backend/store/migrate.py`)

**Symptôme.** La fonction renvoie `[1, 2, …, 13]` mais la base reste vide.

**Reproduction.**

```bash
cd backend
python - <<'EOF'
import os, psycopg
from store.migrate import migrate_postgres
url = os.environ["TEST_DATABASE_URL"]
print(migrate_postgres(url))                       # -> [1, ..., 13]
with psycopg.connect(url) as c:
    print(c.execute("select count(*) from pg_tables where schemaname='public'").fetchone())  # -> (0,)
EOF
```

**Cause probable (vue dans le code).** La connexion est ouverte sans `autocommit` ; le premier
`conn.execute(...)` ouvre une transaction implicite ; `with conn.transaction():` n'est alors
qu'un *savepoint* ; `conn.close()` annule tout. Aucun `conn.commit()` n'existe dans la fonction.

**Conséquence.** `billetterie-api migrate`, `open_postgres()` et donc toute la suite de tests
échouent sur une base vierge (`relation "key_vault" does not exist`). Je ne sais pas pourquoi
cela semblerait fonctionner sur votre machine : **à confirmer** (autre version de psycopg ? base
déjà migrée autrement ?).

**Correctif suggéré (non appliqué).** `psycopg.connect(database_url, autocommit=True)`, ou un
`conn.commit()` après chaque migration.

## Bug 2 — un doublon de scan « empoisonne » la connexion partagée (`store/admissions.py`, `store/store.py`)

**Symptôme.** Après le 1er doublon sur `POST /api/scan`, toutes les requêtes suivantes échouent avec
`psycopg.errors.InFailedSqlTransaction: current transaction is aborted`.

**Reproduction.** Le test existant le met en évidence (une fois la base migrée, cf. bug 1) :

```bash
cd backend
pytest tests/test_scan_and_tickets_e2e.py::test_scan_admit_duplicate_and_wrong_event
# -> échoue à la ligne 121 (2e scan du même billet) : InFailedSqlTransaction
```

**Cause (vue dans le code).** `try_insert_admitted()` exécute un `INSERT` qui viole l'index unique
`idx_admissions_admitted_once`, attrape l'exception et renvoie `False`. Le `Store` n'a qu'une seule
connexion (`_pg`) et ne fait **jamais de `rollback`** : la transaction reste en état d'erreur pour
toutes les requêtes suivantes, y compris celles du `session_middleware` de `http_layer/app.py`
(`auth_svc.validate_session`). **Toute requête authentifiée de l'API est donc bloquée** jusqu'au
redémarrage du processus.

**Correctif suggéré (non appliqué).** `INSERT … ON CONFLICT DO NOTHING` (plus de dépendance à
l'exception), et/ou `rollback` dans `Store.execute_rowcount` en cas d'exception.

## Observation 3 — test de fenêtre de capability (cause non établie)

`tests/test_scan_and_tickets_e2e.py::test_ticket_tdev_and_capability_window` échoue :
`assert 1790763229 == 1790759629` (écart exact de 3600 s = 1 h entre `exp` et `ends_at`).
Je n'ai pas déterminé si c'est un bug du code ou un effet de fuseau horaire/de l'heure d'été de ma
machine. **Non diagnostiqué.**

## Bug 3 — le travail du `Store` reste non validé tant qu'une autre écriture ne fait pas de `commit` (`store/store.py`)

**Symptôme.** Juste après `POST /api/orders/{id}/mark-paid`, les billets émis sont **invisibles** pour toute
autre connexion PostgreSQL (le module check-in, un outil SQL, un dashboard…), jusqu'à la prochaine écriture du `Store`.

**Reproduction.** Test marqué `xfail` : `backend/tests/checkin/test_3a_visibility.py`.

```bash
cd backend
pytest tests/checkin/test_3a_visibility.py -rx   # XFAIL tant que le bug existe (XPASS une fois corrigé)
```

**Cause (vue dans le code et mesurée).** `Store.fetchone/fetchall` ne valident jamais, donc une lecture ouvre une
transaction implicite (`transaction_status = INTRANS`). Un `with store.transaction():` exécuté ensuite n'est plus
qu'un *savepoint* : rien n'est validé à sa sortie. Seul le prochain `Store.execute*()` (qui fait `commit()`) valide
tout ce qui était en attente.

**Conséquence.** Sur un site calme, un billet acheté peut rester invisible de l'extérieur plusieurs secondes ou
minutes. Pour le check-in : un billet tout juste acheté est vu `unknown` par le module (qui lit avec sa propre
connexion). Les tests du module valident explicitement la connexion du 3A après leur préparation
(fixture `commit_3a`) ; **ce contournement n'existe pas en production.**

**Correctif suggéré (non appliqué).** `commit()` à la sortie de `Store.transaction()` (si on est au niveau le plus
externe) et `rollback()` sur exception ; ou `autocommit=True` avec des transactions explicites.

## Observation 4 — deux billets d'une même commande peuvent tirer le même numéro public (`store/pass_serial.py`)

`next_pass_ref()` tire 4 chiffres au hasard et vérifie en base qu'ils sont libres, mais `orders/service.py` (`mint`) alloue **tous** les numéros
d'une commande **avant d'insérer le moindre billet** : le contrôle ne voit pas les numéros de la même commande. Deux billets de la même
commande peuvent donc obtenir le même `TDEV-YYYY-NNNN`, ce qui viole `tickets_serial_key` (`UniqueViolation`, commande non réglée).
Risque de collision au sein d'une commande de *n* billets parmi 10 000 numéros : ≈ 1 − e^(−n²/20 000) — **≈ 0,1 % pour 5 billets, ≈ 39 % pour 100**.
Reproduction : `tests/load/seed.py` avec des commandes de 100 billets (le seed utilise 5 et réessaie).
Autre limite de conception (pas un bug) : 4 chiffres = **≈ 10 000 billets par an au maximum**.

## Observation 5 — le limiteur de `/api/scan` est très bas pour un site derrière une seule IP (`http_layer/middleware/rate_limit.py`)

`ScanRateLimitMiddleware` : 120 requêtes par minute **par IP** sur `/api/scan*`. La charge nominale supposée (300 scans/min) depuis un même site
(probablement une seule IP publique par NAT) en rejette **38 %** (HTTP 429), mesuré (`PERF.md` §7). `/api/checkin/*` n'y est pas soumis
(limiteur par terminal dans le module).

## Observation 6 (environnement, pas un défaut du 3A ni du module) — `uvicorn --workers` sous Windows

Des requêtes restent bloquées 15 à 30 s (`accept()` bloquant du socket partagé entre workers). Détails et preuves : `PERF.md` §8.

## Message prêt à envoyer à Trésor (version courte, WhatsApp)

> Salut Trésor 👋 J'ai trouvé 3 problèmes dans le backend 3A (je n'ai rien modifié chez toi) :
>
> 1️⃣ `migrate_postgres()` (store/migrate.py) dit que les migrations 1 à 13 sont faites, mais la base reste vide. Il manque un commit. Ça marche chez toi ?
>
> 2️⃣ Après un doublon sur `POST /api/scan`, la connexion reste cassée : toutes les requêtes suivantes plantent (`InFailedSqlTransaction`) jusqu'au redémarrage. Le test `test_scan_admit_duplicate_and_wrong_event` le montre.
>
> 3️⃣ Après un paiement, les billets restent non validés côté base tant qu'une autre écriture du Store ne fait pas `commit` : une autre connexion (check-in, dashboard) ne les voit pas tout de suite. Test qui le montre : `tests/checkin/test_3a_visibility.py` (branche feat/checkin).
>
> (+ deux points mineurs : numéros de série `TDEV-…` dupliqués possibles dans une grosse commande, et limiteur de /api/scan à 120/min par IP qui rejette 38 % d'un trafic nominal.)
>
> Détails dans `docs/checkin/BUGS_3A.md`. Tu peux confirmer ? Tu les corriges ou je te propose un correctif ? 🙏
