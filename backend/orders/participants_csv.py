"""Admin export: one CSV row per order with registration form fields."""

from __future__ import annotations

import csv
import io
from typing import Any

from orders import registration as reg
from store import orders as orders_repo
from store import tickets as tickets_repo
from store.store import Store

CSV_HEADERS: list[tuple[str, str]] = [
    ("nom", "Nom"),
    ("prenom", "Prénom"),
    ("email", "E-mail"),
    ("telephone", "Téléphone"),
    ("ville", "Ville"),
    ("pays", "Pays"),
    ("pass", "Type de pass"),
    ("numeros_serie", "Numéros de série"),
    ("statut_commande", "Statut commande"),
    ("tranche_age", "Tranche d'âge"),
    ("genre", "Genre"),
    ("situation", "Situation"),
    ("domaine", "Domaine d'activité"),
    ("etablissement", "Établissement"),
    ("niveau_numerique", "Niveau numérique"),
    ("motivations", "Motivations"),
    ("sujets", "Sujets"),
    ("attentes", "Attentes"),
    ("participation_anterieure", "Participation antérieure"),
    ("appreciation_editions", "Appréciation éditions passées"),
    ("profils_rencontrer", "Profils à rencontrer"),
    ("decouverte_festival", "Découverte du festival"),
    ("recommandation", "Recommandation"),
    ("reste_informe", "Reste informé(e)"),
    ("canal_prefere", "Canal préféré"),
    ("consentement_donnees", "Consentement données"),
    ("consentement_marketing", "Consentement marketing"),
]


def _yes_no(value: Any) -> str:
    if value is True or value == "yes":
        return "Oui"
    if value is False or value == "no":
        return "Non"
    return ""


def _join_list(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    return ", ".join(str(v) for v in value if v)


def _row_for_order(st: Store, order_id: str, order_row) -> dict[str, str] | None:
    tickets = tickets_repo.list_tickets_for_order(st, order_id)
    if not tickets:
        return None
    form = reg.parse_form(getattr(order_row, "registration_form", None))
    type_names: list[str] = []
    serials: list[str] = []
    for t in tickets:
        serials.append(t.serial or "")
        row = st.fetchone("SELECT name FROM ticket_types WHERE id = ?", (t.ticket_type_id,))
        if row:
            name = row["name"] if hasattr(row, "keys") else row[0]
            type_names.append(str(name))
    pass_label = " + ".join(dict.fromkeys(type_names)) or "Pass Festival"
    first = str(form.get("first_name") or order_row.buyer_first_name or "").strip()
    last = str(form.get("last_name") or order_row.buyer_last_name or "").strip()
    email = str(form.get("email") or order_row.buyer_email or "").strip()
    return {
        "nom": last or order_row.buyer_name,
        "prenom": first,
        "email": email,
        "telephone": str(form.get("phone") or ""),
        "ville": str(form.get("city") or ""),
        "pays": str(form.get("country") or ""),
        "pass": pass_label,
        "numeros_serie": ", ".join(s for s in serials if s),
        "statut_commande": order_row.status,
        "tranche_age": str(form.get("age_range") or ""),
        "genre": str(form.get("gender") or ""),
        "situation": str(form.get("situation") or ""),
        "domaine": str(form.get("activity_domain") or ""),
        "etablissement": str(form.get("school_program") or ""),
        "niveau_numerique": str(form.get("digital_level") or ""),
        "motivations": _join_list(form.get("participation_reasons")),
        "sujets": _join_list(form.get("topics")),
        "attentes": str(form.get("expectations") or ""),
        "participation_anterieure": str(form.get("prior_participation") or ""),
        "appreciation_editions": str(form.get("prior_liked") or ""),
        "profils_rencontrer": str(form.get("want_to_meet") or ""),
        "decouverte_festival": str(form.get("discovery_channel") or ""),
        "recommandation": str(form.get("referred_by") or ""),
        "reste_informe": _yes_no(form.get("stay_informed")),
        "canal_prefere": str(form.get("preferred_channel") or ""),
        "consentement_donnees": _yes_no(form.get("consent_data_processing")),
        "consentement_marketing": _yes_no(form.get("consent_marketing")),
    }


def build_participants_csv(st: Store, event_id: str) -> tuple[bytes, int]:
    """UTF-8 CSV with BOM for Excel. Returns (payload, data_row_count)."""
    orders = orders_repo.list_orders_for_event(st, event_id)
    rows: list[dict[str, str]] = []
    for o in orders:
        built = _row_for_order(st, o.id, o)
        if built:
            rows.append(built)
    if not rows:
        return b"", 0
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow([label for _, label in CSV_HEADERS])
    keys = [k for k, _ in CSV_HEADERS]
    for row in rows:
        writer.writerow([row.get(k, "") for k in keys])
    return ("\ufeff" + buf.getvalue()).encode("utf-8"), len(rows)
