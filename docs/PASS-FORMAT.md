# Format pass QR (Chantier 3A)

Contrat d'emission et de verification du contenu encode dans le QR billet (scan via API en ligne).

## Forme du token

```text
chantier3a.<payload_b64url>.<signature_b64url>
```

- Prefixe fixe : `chantier3a` (segment 1).
- Payload : JSON canonique signe en Ed25519 (segment 2), encodage base64url **sans padding**.
- Signature : 64 octets Ed25519 sur les octets UTF-8 du JSON (segment 3), base64url sans padding.

La canonicalisation JSON reprend le comportement HTML-safe de Go : dans les chaines, `&`, `<` et `>` sont echappes en `\u0026`, `\u003c`, `\u003e`.

## Champs payload (version 1)

Ordre d'emission canonique (cle insertion) :

| Cle | Type | Obligatoire | Description |
|-----|------|-------------|-------------|
| `v` | int | oui | Version du format (1). |
| `tid` | string | oui | Identifiant technique billet (ULID), dedupe admission. |
| `ref` | string | oui | Reference publique `TDEV-YYYY-NNNN` (affichee participant, stockee en BDD). |
| `eid` | string | oui | Evenement. |
| `tt` | string | oui | Type de billet / pass tier. |
| `kid` | string | oui | Identifiant cle Ed25519 evenement. |
| `sub` | string | oui | Detenteur (user id ou vide). |
| `nm` | string | oui | Nom porteur. |
| `iat` | int | oui | Emission (Unix secondes UTC). |
| `nbf` | int | oui | Debut validite (Unix s), egal a `starts_at` evenement. |
| `exp` | int | oui | Fin validite (Unix s), egal a `ends_at` evenement (borne haute exclusive). |
| `seat` | string | non | Place ; omis si vide. |

### Fenetre evenement

- A l'emission : `nbf = starts_at`, `exp = ends_at`, **sans marge**.
- Meme fenetre pour tous les pass tiers ; la distinction produit reste dans `tt` / pass tier.
- Au scan : refus si `nbf <= 0` ou `exp <= 0` (pas de retrocompatibilite billets sans fenetre).

### Reference publique `ref`

- Format : `TDEV-<annee>-<seq>` avec `<seq>` sur 4 chiffres (ex. `TDEV-2026-0042`).
- Compteur atomique par annee calendaire a l'emission.
- `tickets.serial` en base reprend la meme valeur que `ref` dans le token.

## Verification

1. Decouper le token, verifier le prefixe et le base64url.
2. Verifier la signature Ed25519 avec la cle publique `kid` de l'evenement.
3. Parser le JSON : champs inconnus interdits ; types numeriques stricts pour `v`, `iat`, `nbf`, `exp`.
4. Exiger `v == 1`, fenetre `nbf` / `exp` strictement positive.
5. Appliquer `now >= nbf` (inclus) et `now < exp` (exclus).

Erreurs normalisees : `malformed`, `unsupported_version`, `bad_signature`, `not_yet_valid`, `expired`, `unknown_kid`.

## Jeu de conformance

Vecteurs figes : [`pass-format-vectors.json`](pass-format-vectors.json), executes par `tests/test_capability_conformance.py`.

## Implementation

- Emission / signature : [`tickets/capability.py`](../tickets/capability.py), [`events/issue.py`](../events/issue.py).
- Compteur `ref` : [`store/pass_serial.py`](../store/pass_serial.py).
- Paiement et payload : [`orders/service.py`](../orders/service.py).
- Scan : [`scan/admission.py`](../scan/admission.py).

Le champ API `capability` **est** la chaine complete a encoder dans le QR (pas de second encodage HMAC).
