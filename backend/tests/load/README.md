# Tests de charge du module check-in (TDEV-56)

Résultats et analyse : [`docs/checkin/PERF.md`](../../../docs/checkin/PERF.md). Hypothèses de charge : `docs/checkin/DESIGN.md` §4.1
(3 000 participants, 10 terminaux, pic 300 scans/min, lots de 200 opérations) — **des suppositions, pas des données du projet**.

**Base jetable uniquement.** Ces scripts vident des tables (`TRUNCATE scan_logs CASCADE`) : n'utilisez jamais une vraie base.
Les scripts refusent de tourner si le nom de la base ne finit pas par `_perf` ou `_test`.

## 1. Une base PostgreSQL réaliste

`fsync` actif et disque réel (une base en `tmpfs` flatte les temps d'écriture) :

```bash
docker run -d --name tdev-checkin-perf-pg -p 127.0.0.1:5434:5432 \
  -e POSTGRES_USER=checkin_perf -e POSTGRES_PASSWORD=checkin_perf -e POSTGRES_DB=chantier3a_perf \
  postgres:16-alpine -c max_connections=200
export CHECKIN_LOAD_DATABASE_URL="postgresql://checkin_perf:checkin_perf@127.0.0.1:5434/chantier3a_perf?sslmode=disable"
```

## 2. Jeu de données (billets signés réels, via l'API 3A en mémoire)

```bash
python tests/load/seed.py --tickets 3000      # ~40 s ; écrit tests/load/.seed.json (ignoré par git)
```

Le 3A tire 4 chiffres au hasard pour chaque billet d'une commande **avant** d'en insérer un seul : les commandes sont donc
petites (5 billets) et réessayées en cas de collision (voir `docs/checkin/BUGS_3A.md`, observation 4).

## 3. Démarrer le service

```bash
CHECKIN_DATABASE_URL="$CHECKIN_LOAD_DATABASE_URL" uvicorn checkin.asgi:app --port 8090 --workers 4
# référence « avant » : l'application 3A seule (POST /api/scan)
LEGACY_DISABLE_RATE_LIMIT=1 uvicorn --app-dir tests/load legacy_app:app --port 8091
```

⚠️ `/api/checkin/health` ne prouve que **un** worker prêt. Sous Windows les workers démarrent un par un (plusieurs secondes) :
attendez que chacun ait ouvert son pool avant d'ouvrir le trafic (voir `PERF.md`).

## 4. Générer la charge

**Locust** (`locustfile.py`, scénarios `checkin`, `scan`, `burst`, `legacy3a`) :

```bash
pip install -e ".[load]"
SCENARIO=checkin locust -f tests/load/locustfile.py --headless -u 11 -r 11 -t 60s --host http://127.0.0.1:8090
```

> Le `locustfile.py` **n'a pas pu être exécuté sur la machine de développement** : une stratégie de contrôle d'application
> de Windows bloque la bibliothèque native de `gevent` (`_gevent_c_greenlet_primitives`). Il est fourni, relu, mais non testé ici.

**`loadgen.py`** — mêmes scénarios en Python pur (`httpx` + threads), utilisé pour toutes les mesures de `PERF.md` :

```bash
python tests/load/loadgen.py --scenario checkin --users 10 --syncers 1 --duration 45 --sync-wait 15     # charge nominale
python tests/load/loadgen.py --scenario scan    --users 30 --wait-min 0.01 --wait-max 0.03 --duration 30  # saturation
python tests/load/loadgen.py --scenario burst   --users 10 --sync-wait 0 --duration 30                   # 10 lots de 200 en même temps
python tests/load/loadgen.py --scenario checkin --users 10 --syncers 10 --sync-wait 3 --duration 30      # rafale mixte
python tests/load/loadgen.py --scenario legacy3a --host http://127.0.0.1:8091 --users 10 --dup 0
```

Le générateur de charge tourne sur la **même machine** que le service et la base : ses chiffres sont pessimistes pour le service
et les temps de calcul du générateur y sont inclus.

## 5. Autres mesures

```bash
python tests/load/bench_bulk.py --ops 200 --runs 30      # insertions ligne par ligne vs en lot
python tests/load/explain.py --scale 200000 > explain.md # EXPLAIN (ANALYZE, BUFFERS) avec le SQL réel du module
```
