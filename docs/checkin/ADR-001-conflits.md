# ADR-001 — Résolution des conflits de scan hors ligne simultanés (TDEV-55)

Statut : **proposé** (à valider par Trésor, Rodrigue, Marina-Gracia, Abdoul-Rachid).
Date : 2026-09-30. Auteure : Edéda BLEOUSSI.

## Contexte

Deux terminaux hors ligne peuvent chacun accepter (`valid`) le même billet au même poste, puis
synchroniser dans n'importe quel ordre, avec des horloges de téléphone imprécises.
Le 3A sait seulement qu'« il n'y a qu'une admission par billet » (`idx_admissions_admitted_once`),
et son `POST /api/scan` ne journalise que les `admitted`. Le 3B, lui, détecte le doublon par
couple (billet, poste) et n'envoie que sa décision.

Il faut une règle qui :
1. est **déterministe** et **indépendante de l'ordre d'arrivée** des lots ;
2. est **idempotente** (rejouer ne change rien) ;
3. **n'efface rien** (le perdant reste journalisé et devient un conflit visible).

Fait irréductible : si deux portes hors ligne ont chacune laissé entrer quelqu'un, **personne ne
peut l'empêcher après coup**. La synchronisation rend le double passage *visible*, pas *évitable*.
Le conflit est donc un signalement pour un superviseur, pas une annulation.

## Décision

### 1. L'état est une fonction de l'ensemble des journaux
Pour (ticket, station), l'ensemble des **prétendants** (`scan_logs.is_claim = true`) est trié par

```
clé = (clock_suspect ASC, corrected_evaluated_at ASC, operation_id ASC)
```

Les `max_uses` premiers occupent `use_index = 0 … max_uses-1` dans `station_consumptions`. Les autres sont
**perdants**. Comme `scan_logs` est immuable, que `corrected_evaluated_at`, `clock_suspect` et `is_claim` sont figés à
l'insertion, et que la clé est un ordre total, le résultat ne dépend que de l'ensemble des logs, pas de l'ordre dans
lequel on les a reçus.

**Monotonie** : ajouter un log ne peut que *dégrader* le rang des autres (jamais l'améliorer). Un perdant le reste ;
un gagnant peut perdre sa place. Aucune ligne de `scan_conflicts` n'est donc jamais supprimée.

### 2. Un prétendant est…
Une opération dont, à l'insertion :
- le terminal a rapporté `valid` (ou scan en ligne répondu `valid`) ;
- **et** des contrôles *propres à l'opération ou statiques* passent : événement cohérent, billet connu, billet non annulé à
  `corrected_evaluated_at`, règle du poste avec `max_uses > 0`, capability non marquée fausse si fournie.

Ces contrôles ne dépendent **pas** de l'état de consommation courant (sinon l'ordre d'arrivée fuirait dans la décision).
Une opération qui échoue à ces contrôles est **journalisée, non prétendante**, avec un conflit de type `LATE_REVOKED` ou
`NOT_AUTHORIZED_SERVER_SIDE` (`winning_log_id` NULL) *si le terminal avait rapporté `valid`*.
Une opération où le terminal rapporte `alreadyScanned`, `invalid`, etc. est de la **preuve d'audit**, pas un prétendant.

### 3. Correction d'horloge : par lot, figée, non lissée
```
clock_offset(lot)        = server_received_at(lot) − device_sent_at(lot)
corrected_evaluated_at   = device_evaluated_at + clock_offset(lot)
```
Scans en ligne : `corrected = server_received_at` (décalage 0). Le décalage est **stocké dans chaque log**.

*Pourquoi pas « lissé par terminal » (proposition initiale)* : un décalage lissé dépend de l'historique des lots reçus donc de leur
ordre, ce qui fait dépendre la clé de tri de l'ordre d'arrivée. On garde un lissage uniquement en diagnostic
(`checkin_terminals.clock_offset_ms`). Limite acceptée : le décalage par lot inclut le délai réseau d'envoi (quelques centaines
de ms) ; à l'échelle des seuils ci-dessous, c'est négligeable. Recommandation à Rodrigue : **re-horodater `device_sent_at` à chaque
tentative d'envoi** (et non à la création du lot), pour que le décalage reste proche de la réalité.

**Horloge suspecte** (`clock_suspect = true`, seuils configurables, valeurs par défaut prudentes, à valider par Abdoul-Rachid) :
- `|clock_offset| > CHECKIN_CLOCK_OFFSET_MAX_SECONDS` (défaut 300) ;
- `corrected_evaluated_at > server_received_at + CHECKIN_CLOCK_FUTURE_TOLERANCE_SECONDS` (défaut 60) ;
- `corrected_evaluated_at < server_received_at − CHECKIN_MAX_OPERATION_AGE_HOURS` (défaut 72 h).

Un prétendant suspect est classé **après** tous les non suspects (premier élément de la clé) : un terminal dont l'horloge est fausse
(ou malveillante) **ne peut pas gagner** un conflit contre un scan plausible en antidatant le sien. S'il est seul, il est accepté et
signalé (`CLOCK_SUSPECT`, pour relecture humaine).

### 4. Types de conflit (un par perdant)
Appliqués dans cet ordre de priorité (déterministe) :

| Priorité | Type | Condition |
|---|---|---|
| 1 | `LATE_REVOKED` | billet `void`/`refunded` avec `voided_at ≤ corrected_evaluated_at` (ou statut non valide sans `voided_at`) |
| 2 | `NOT_AUTHORIZED_SERVER_SIDE` | le terminal a dit `valid`, mais billet inconnu / autre événement / poste non autorisé par `checkin_station_rules` |
| 3 | `CROSS_TERMINAL_DOUBLE_ADMISSION` | perdant prétendant, terminal ≠ terminal du gagnant : **cas critique**, quelqu'un est réellement passé deux fois |
| 4 | `SAME_TERMINAL_REPLAY` | perdant prétendant, même terminal que le gagnant : bénin (doublon local, réinstallation…) |
| — | `CLOCK_SUSPECT` | prétendant suspect **sans concurrent** (il a pris la place) : relecture humaine ; sinon la colonne booléenne `scan_conflicts.clock_suspect` est à `true` |

### 5. Concurrence : verrou consultatif transactionnel
Choix : `pg_advisory_xact_lock(hashtextextended(ticket_id || ':' || station, 0))`, pris **dans l'ordre trié des clés** pour tout le lot, avant toute écriture.

| Option | Verdict |
|---|---|
| `SELECT … FOR UPDATE` sur la consommation | Insuffisant : pour la **première** consommation la ligne n'existe pas, donc rien à verrouiller ; deux lots concurrents passeraient tous deux. |
| Contrainte unique + `ON CONFLICT DO NOTHING` seule | Garantit un seul occupant mais **ne sait pas faire basculer le gagnant** quand un scan plus ancien arrive tard (il faut relire l'ensemble des prétendants et réécrire). Conservée comme **filet de sécurité** (`PRIMARY KEY (ticket_id, station, use_index)`). |
| **Verrou consultatif par (ticket, station)** | Sérialise exactement la zone critique, sans ligne préalable, se libère au `COMMIT`/`ROLLBACK`, pas de verrous persistants. Une collision de hash (64 bits) ne coûte qu'une sérialisation en trop. |

Isolation `READ COMMITTED` suffit : chaque requête *après* l'obtention du verrou voit les lots déjà validés.
Le verrou est acquis **avant** l'`INSERT` des logs, ce qui évite qu'un lot concurrent classe sans voir l'autre.
`lock_timeout = 2 s` ; dépassement → `503 service_busy`, le lot entier est rejouable sans danger.

## Pseudo-code

```text
fonction traiter_lot(lot, principal):
    valider_enveloppe(lot)                       # taille, terminal, rôle   → erreur de lot (4xx)
    received_at ← now()
    offset      ← received_at − lot.device_sent_at
    pour op dans lot.operations:                 # fonctions pures (domain.py)
        r ← valider_operation(op)                # station connue, décision connue, champs → sinon rejected(code)
        si r.ok : candidats.ajouter(construire_log(op, offset, received_at, contexte))

    BEGIN
      verrouiller(trier(clés (ticket, station) des candidats))        # pg_advisory_xact_lock, ordre trié
      nouveaux ← INSERT … ON CONFLICT (operation_id) DO NOTHING RETURNING
      # opérations absentes de `nouveaux` : rejeu
      pour op dans candidats \ nouveaux:
          si payload_hash(op) ≠ stocké            → rejected(operation_id_reuse)
          sinon                                    → already_processed(résultat d'origine)
      contexte ← charger_en_lot(billets, règles, prétendants, consommations)   # 3 requêtes, pas de N+1
      pour groupe (ticket, station) dans nouveaux groupés:
          prétendants ← existants ∪ nouveaux du groupe
          rang        ← trier(prétendants, clé)
          attribuer   ← rang[0 : max_uses]                                     # use_index = position
          réécrire station_consumptions du groupe pour refléter `attribuer`    # UPSERT, bascule de gagnant
          pour p dans rang[max_uses :]: upsert scan_conflicts(type calculé, gagnant)
          pour op_non_prétendante_rapportée_valid: upsert scan_conflicts(LATE_REVOKED | NOT_AUTHORIZED_SERVER_SIDE)
      statut(op) ← 'conflict' si op a un conflit, sinon 'accepted'
      (ack_status est figé dans le log à l'insertion)
    COMMIT
    retourner réponses dans l'ordre reçu
```

`server_decision` d'une opération hors ligne = décision serveur à l'insertion : `valid` si elle occupe une place à l'issue du
classement, `already_scanned` si elle perd, `revoked` / `not_authorized` / `unknown` / `wrong_event` / `invalid` sinon.

## Conséquences

- (+) Convergence prouvable : l'état est `f(ensemble des logs)`. Test de propriété : toutes les permutations d'arrivée d'un même jeu de lots donnent les mêmes `station_consumptions` et `scan_conflicts`.
- (+) Rejeu sans effet (unicité `operation_id` + `payload_hash`).
- (+) Rien n'est effacé ; l'audit complet reste dans `scan_logs`.
- (−) Le « gagnant » peut changer après coup : un terminal/agent déjà informé (`valid`) peut apparaître perdant. C'est voulu, et `ack_status` conserve ce qui a été répondu.
- (−) Un scan en ligne répondu `valid` peut devenir perdant si un scan hors ligne *plus ancien* est synchronisé plus tard : les deux personnes sont réellement entrées → `CROSS_TERMINAL_DOUBLE_ADMISSION`, à traiter par un humain.
- (−) La précision dépend de l'horloge des téléphones ; l'antidatage est neutralisé par `clock_suspect`, pas par un mécanisme cryptographique (fenêtre d'incertitude résiduelle < seuil configuré).
- (−) Le serveur ne peut pas re-vérifier la signature d'un QR sans `capability` (non stockée) : tant que le terminal ne l'envoie pas, `capability_verified = NULL` et la confiance repose sur le rôle `scanner` du terminal authentifié.

## Alternatives écartées

- **Premier arrivé gagne** : dépend de l'ordre de synchronisation, non reproductible.
- **Offset lissé par terminal** : voir §3.
- **Écrire dans `admissions`** : interdit par la règle « ne pas modifier le 3A » et laisserait une seule admission par billet, ce qui ne représente pas les consommations par poste.
- **Suppression / annulation du perdant** : contredit l'exigence d'audit et l'impossibilité physique d'annuler un passage.

## Points à valider

Voir `OPEN_QUESTIONS.md` : ré-entrée (`max_uses`), seuils d'horloge, révocation et lots antérieurs, `capability` dans `/sync`.
