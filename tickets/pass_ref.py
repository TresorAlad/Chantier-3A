"""Public pass reference format TDEV-YYYY-NNNN (suffixe 4 chiffres)."""

from __future__ import annotations

import re
import secrets

REF_PATTERN = re.compile(r"^TDEV-\d{4}-\d{4}$")


def format_pass_ref(year: int, suffix: int) -> str:
    """Format a public pass reference for the given calendar year and 4-digit suffix."""
    if suffix < 0 or suffix > 9999:
        raise ValueError("pass suffix must be between 0 and 9999")
    return f"TDEV-{year}-{suffix:04d}"


def random_pass_suffix() -> int:
    """Draw a random 4-digit suffix (0000-9999)."""
    return secrets.randbelow(10_000)
