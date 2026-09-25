"""Festival pass tiers: catalog and defaults for ticket types.

Prices use the event currency. For FCFA (West Africa), set the event to ``XOF``:
``price_minor`` is whole francs (exponent 0), e.g. 5000 FCFA -> ``price_minor: 5000``.
"""

from __future__ import annotations

PASS_TIER_STUDENT = "student"
PASS_TIER_STANDARD = "standard"
PASS_TIER_VIP = "vip"

ALL_PASS_TIERS = (PASS_TIER_STUDENT, PASS_TIER_STANDARD, PASS_TIER_VIP)

# Standard and VIP prices are not defined yet; only the student pass is on sale.
ENABLED_PASS_TIERS = (PASS_TIER_STUDENT,)

PASS_TIER_LABELS: dict[str, str] = {
    PASS_TIER_STUDENT: "Pass étudiant",
    PASS_TIER_STANDARD: "Pass standard",
    PASS_TIER_VIP: "Pass VIP",
}

STUDENT_PASS_TICKET_TYPE_BODY: dict = {
    "name": PASS_TIER_LABELS[PASS_TIER_STUDENT],
    "description": "",
    "price_minor": 0,
    "quantity_total": 0,
    "max_per_order": 1,
    "status": "active",
    "sort_order": 0,
    "product_kind": "ticket",
    "pass_tier": PASS_TIER_STUDENT,
}


def pass_tier_catalog() -> list[dict]:
    """Tiers exposed to the storefront (enabled tiers only)."""
    out: list[dict] = []
    for tier in ENABLED_PASS_TIERS:
        entry: dict = {
            "id": tier,
            "label": PASS_TIER_LABELS[tier],
            "available": True,
        }
        if tier == PASS_TIER_STUDENT:
            entry["price_minor"] = 0
        out.append(entry)
    return out


def normalize_pass_tier(value: object) -> str | None:
    """Return a known tier slug or None when absent/empty."""
    if value is None:
        return None
    tier = str(value).strip().lower()
    if not tier:
        return None
    return tier
