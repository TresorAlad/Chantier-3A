"""Validation for pass registration fields on checkout."""

from __future__ import annotations

from dataclasses import dataclass

from events.passes import PASS_TIER_STUDENT
from store import ticket_types as tt_repo

MAX_NAME = 120
MAX_SCHOOL = 200
MAX_TEXT = 4000


@dataclass
class PassRegistration:
    """Passregistration."""
    first_name: str
    last_name: str
    email: str
    school_name: str
    motivation: str
    wish: str


class RegistrationError(ValueError):
    """Registrationerror."""


def order_needs_pass_registration(store, event_id: str, ticket_type_ids: list[str]) -> bool:
    """Return True if any line item is a student pass tier."""
    for tt_id in ticket_type_ids:
        tt = tt_repo.get_ticket_type_by_id(store, tt_id)
        if tt.event_id != event_id:
            continue
        if tt.pass_tier == PASS_TIER_STUDENT:
            return True
    return False


def normalize_registration(
    *,
    email: str,
    first_name: str = "",
    last_name: str = "",
    legacy_name: str = "",
    school_name: str = "",
    motivation: str = "",
    wish: str = "",
    required: bool,
) -> PassRegistration:
    """Validate and normalize registration; raise RegistrationError if invalid."""
    email = email.strip()
    first_name = first_name.strip()
    last_name = last_name.strip()
    legacy_name = legacy_name.strip()
    if not first_name and not last_name and legacy_name:
        parts = legacy_name.split(None, 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
    school_name = school_name.strip()
    motivation = motivation.strip()
    wish = wish.strip()

    if not required:
        display = f"{first_name} {last_name}".strip() or legacy_name
        return PassRegistration(
            first_name=first_name,
            last_name=last_name,
            email=email,
            school_name=school_name,
            motivation=motivation,
            wish=wish,
        )

    missing: list[str] = []
    if not first_name:
        missing.append("first_name")
    if not last_name:
        missing.append("last_name")
    if not email:
        missing.append("email")
    if not school_name:
        missing.append("school_name")
    if not motivation:
        missing.append("motivation")
    if not wish:
        missing.append("wish")
    if missing:
        raise RegistrationError(f"required registration fields: {', '.join(missing)}")

    _check_len("first_name", first_name, MAX_NAME)
    _check_len("last_name", last_name, MAX_NAME)
    _check_len("school_name", school_name, MAX_SCHOOL)
    _check_len("motivation", motivation, MAX_TEXT)
    _check_len("wish", wish, MAX_TEXT)

    return PassRegistration(
        first_name=first_name,
        last_name=last_name,
        email=email,
        school_name=school_name,
        motivation=motivation,
        wish=wish,
    )


def _check_len(field: str, value: str, limit: int) -> None:
    """Internal: check len."""
    if len(value) > limit:
        raise RegistrationError(f"{field} exceeds {limit} characters")
