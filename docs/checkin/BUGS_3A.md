# Bugs constatés dans le 3A (corrections proposées sur `feat/checkin`)

Constatés le 2026-09-30 sur `main` (commit `208f0b6`), avec PostgreSQL 16 (Docker) et
psycopg 3.3.6, Python 3.12.9. Chacun était reproductible comme décrit ci-dessous.

> **Mise à jour du 2026-10-01 (corrections sur la branche `feat/checkin`).** À la demande d'Edéda, les bugs 2, 3 et 4,
> l'observation 3 (test périmé) et l'observation 4 sont **corrigés dans cette branche**, en commits séparés, pour relecture par Trésor.
> Ils modifient du code 3A (`store/`, `auth/`, `orders/`) : c'est à valider explicitement. Les observations 5 et 6 ne sont pas des défauts à corriger
> dans le code (voir leur section). Résultat : suite complète **SQLite : 92 réussis, 0 échec** (8 échecs avant) ; **PostgreSQL : 177 réussis, 0 échec**.

> **Historique** : le `main` du 3A avait avancé de 34 commits (dernier : `23ff158`) : bug 1 corrigé en amont par Trésor (`d3b4ca8`) ; bugs 2 et 3 toujours
> présents à cette date ; bug 4 apparu.

Préparation commune (base jetable, jamais une vraie base : `conftest.py` fait un `TRUNCATE`
de toutes les tables publiques) :

```bash
docker run -d --name pg-test -p 127.0.0.1:5433:5432 \
  -e POSTGRES_USER=checkin_test -e POSTGRES_PASSWORD=checkin_test \
  -e POSTGRES_DB=chantier3a_test postgres:16-alpine
export TEST_DATABASE_URL="postgresql://checkin_test:checkin_test@127.0.0.1:5433/chantier3a_test?sslmode=disable"
```

## Bug 1 — `migrate_postgres()` n'enregistre rien (`backend/store/migrate.py`) — CORRIGÉ en amont (Trésor, `d3b4ca8`)

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

## Bug 2 — un doublon de scan « empoisonne » la connexion partagée (`store/admissions.py`, `store/store.py`) — CORRIGÉ sur `feat/checkin`

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

**Correctif appliqué.** `try_insert_admitted()` utilise `INSERT … ON CONFLICT DO NOTHING` et lit le nombre de lignes insérées (un doublon n'est plus une
erreur) ; par sécurité, `Store.execute_rowcount` fait un `rollback()` si une requête échoue, pour qu'aucune erreur ne laisse la connexion partagée dans
l'état « transaction avortée ». Vérifié : `test_scan_admit_duplicate_and_wrong_event` (PostgreSQL) passe et la requête qui suit un doublon répond normalement.

## Observation 3 — test de fenêtre de capability — CAUSE TROUVÉE : test périmé, corrigé

`tests/test_scan_and_tickets_e2e.py::test_ticket_tdev_and_capability_window` échouait (`assert 1790763229 == 1790759629`, écart exact de 3600 s).

**Cause (établie le 2026-10-01).** Ce n'est ni un fuseau horaire ni un bug du code : `orders/service.py` fixe volontairement `nbf` (début de validité du billet) à la
**date de paiement** (« Valid from purchase through event end »), alors que le test attendait encore `nbf == starts_at` de l'événement. Dans le test, l'événement
commence 1 h avant l'achat, d'où les 3600 s. **Correction : le test attend maintenant `nbf == iat`** (le comportement du code n'a pas changé).

## Bug 3 — le travail du `Store` reste non validé tant qu'une autre écriture ne fait pas de `commit` (`store/store.py`) — CORRIGÉ sur `feat/checkin`

**Symptôme.** Juste après `POST /api/orders/{id}/mark-paid`, les billets émis sont **invisibles** pour toute
autre connexion PostgreSQL (le module check-in, un outil SQL, un dashboard…), jusqu'à la prochaine écriture du `Store`.

**Reproduction (avant correction).** Test `backend/tests/checkin/test_3a_visibility.py` (était `xfail`, maintenant un test normal qui passe).

```bash
cd backend
pytest tests/checkin/test_3a_visibility.py   # PostgreSQL requis (TEST_DATABASE_URL) ; échoue si le bug revient
```

**Cause (vue dans le code et mesurée).** `Store.fetchone/fetchall` ne valident jamais, donc une lecture ouvre une
transaction implicite (`transaction_status = INTRANS`). Un `with store.transaction():` exécuté ensuite n'est plus
qu'un *savepoint* : rien n'est validé à sa sortie. Seul le prochain `Store.execute*()` (qui fait `commit()`) valide
tout ce qui était en attente.

**Conséquence.** Sur un site calme, un billet acheté peut rester invisible de l'extérieur plusieurs secondes ou
minutes. Pour le check-in : un billet tout juste acheté est vu `unknown` par le module (qui lit avec sa propre
connexion). Les tests du module valident explicitement la connexion du 3A après leur préparation
(fixture `commit_3a`) ; **ce contournement n'existe pas en production.**

**Correctif appliqué.** (1) `Store.transaction()` ferme d'abord la transaction implicite laissée par une lecture (seulement au niveau le plus externe, grâce à un
compteur de profondeur), de sorte que le bloc est une vraie transaction validée à la sortie, annulée sur exception. (2) Les trois fonctions de `store/orders.py`
(création, annulation, règlement de commande) utilisaient `conn.transaction()` directement : elles passent par `st.transaction()`. (3) `tests/sqlite_store.py`
reçoit `rollback()` et `info` (sans effet) pour que le faux connecteur SQLite reste compatible.
Limite : une lecture isolée laisse toujours une transaction implicite ouverte jusqu'à la prochaine écriture ou `transaction()` ; sans conséquence pour la
visibilité des écritures, qui sont validées.

## Observation 4 — deux billets d'une même commande peuvent tirer le même numéro public (`store/pass_serial.py`) — CORRIGÉ sur `feat/checkin`

`next_pass_ref()` tire 4 chiffres au hasard et vérifie en base qu'ils sont libres, mais `orders/service.py` (`mint`) alloue **tous** les numéros
d'une commande **avant d'insérer le moindre billet** : le contrôle ne voit pas les numéros de la même commande. Deux billets de la même
commande peuvent donc obtenir le même `TDEV-YYYY-NNNN`, ce qui viole `tickets_serial_key` (`UniqueViolation`, commande non réglée).
Risque de collision au sein d'une commande de *n* billets parmi 10 000 numéros : ≈ 1 − e^(−n²/20 000) — **≈ 0,1 % pour 5 billets, ≈ 39 % pour 100**.
Reproduction : `tests/load/seed.py` avec des commandes de 100 billets (le seed utilise 5 et réessaie).

**Correctif appliqué.** `next_pass_ref` reçoit l'ensemble des numéros déjà tirés pour la commande en cours (`taken`) et en redessine un si le numéro y figure ; `orders/service.py` (`mint`) le fournit. Test : `tests/test_pass_serial.py`.
**Non corrigé (décision de conception, à Trésor)** : 4 chiffres = **≈ 10 000 billets par an au maximum**.

## Observation 5 — le limiteur de `/api/scan` est très bas pour un site derrière une seule IP (`http_layer/middleware/rate_limit.py`) — NON MODIFIÉ (choix de politique)

`ScanRateLimitMiddleware` : 120 requêtes par minute **par IP** sur `/api/scan*`. La charge nominale supposée (300 scans/min) depuis un même site
(probablement une seule IP publique par NAT) en rejette **38 %** (HTTP 429), mesuré (`PERF.md` §7). `/api/checkin/*` n'y est pas soumis
(limiteur par terminal dans le module). Je ne change pas cette limite : c'est un réglage anti-abus de Trésor dont la bonne valeur dépend du déploiement.

## Observation 6 (environnement, pas un défaut du 3A ni du module) — RIEN À CORRIGER DANS LE CODE — `uvicorn --workers` sous Windows

Des requêtes restent bloquées 15 à 30 s (`accept()` bloquant du socket partagé entre workers). Détails et preuves : `PERF.md` §8.

## Bug 4 (nouveau sur `main`, constaté le 2026-10-01) — l'inscription par mot de passe et par invitation échoue en HTTP 500 — CORRIGÉ sur `feat/checkin`

`auth.service.signup` (ligne 116) et `signup_with_invite` (ligne 143) appellent `user_store.create_user(st, email, password_hash, name)`, mais
`store/users.py` a été réécrit : `create_user(st, user: UserPartial)`. Résultat : `TypeError: create_user() takes 2 positional arguments but 4 were given`,
masqué par la route en `internal_error` (HTTP 500).

**Reproduction** (sans PostgreSQL : le mode par défaut de la suite 3A, SQLite) :

```bash
cd backend
pytest tests/test_api_smoke.py::test_auth_flow tests/test_visitor_checkout.py::test_signup_with_invite_when_public_signup_off
# -> 8 tests de la suite 3A échouent sur ce main (auth_flow, organizer flow, 5 de test_scan_and_tickets_e2e, signup_with_invite), avant toute modification
```

**Conséquence.** Tant que ce n'est pas corrigé, un agent de scan ne peut pas être créé par mot de passe ni par invitation (reste Google OAuth si utilisé).
Les tests du module check-in créent leurs comptes directement dans le store pour ne pas en dépendre.

**Correctif appliqué.** `create_user(st, UserPartial(email=…, password_hash=ph, name=…))` dans `signup` et `signup_with_invite` (`auth/service.py`). Les 8 tests de la suite 3A qui échouaient (dont ceux de la liste ci-dessus) passent.
