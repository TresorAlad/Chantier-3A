"""Create or update a staff account on the TDEV org (CLI bootstrap-staff)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from auth import service as auth_svc
from auth.password import hash_password
from store import NotFoundError, Store
from store import orgs as orgs_repo
from store import users as user_store

DEFAULT_ORG_SLUG = "tdev"


def bootstrap_staff_account(
    store: Store,
    *,
    email: str,
    password: str,
    name: str,
    org_slug: str = DEFAULT_ORG_SLUG,
    role: str = "owner",
) -> dict[str, str]:
    if os.getenv("CHANTIER3A_BOOTSTRAP_STAFF", "").strip().lower() not in ("1", "true", "yes", "on"):
        raise SystemExit(
            "billetterie-api: definissez CHANTIER3A_BOOTSTRAP_STAFF=1 pour creer ou mettre a jour un compte staff."
        )
    if len(password) < auth_svc.MIN_PASSWORD_LENGTH:
        raise SystemExit(
            f"billetterie-api: mot de passe trop court (minimum {auth_svc.MIN_PASSWORD_LENGTH} caracteres)."
        )
    if role not in ("owner", "admin", "scanner"):
        raise SystemExit("billetterie-api: role invalide (owner, admin, scanner).")

    org = orgs_repo.get_org_by_slug(store, org_slug)
    norm = email.strip().lower()
    now = datetime.now(timezone.utc)

    try:
        existing = user_store.get_user_by_email(store, norm)
        user_store.update_password_hash(store, existing.id, hash_password(password))
        user_id = existing.id
        user_action = "mot de passe mis a jour"
    except NotFoundError:
        user = auth_svc.signup(store, norm, password, name.strip() or norm.split("@")[0])
        user_id = user.id
        user_action = "compte cree"

    try:
        orgs_repo.get_org_member_role(store, org.id, user_id)
        store.execute(
            "UPDATE org_members SET role = ? WHERE org_id = ? AND user_id = ?",
            (role, org.id, user_id),
        )
        member_action = f"role {role} sur org {org_slug}"
    except NotFoundError:
        orgs_repo.add_org_member(store, org.id, user_id, role, now)
        member_action = f"ajoute comme {role} sur org {org_slug}"

    return {
        "email": norm,
        "user_action": user_action,
        "member_action": member_action,
        "org_id": org.id,
    }
