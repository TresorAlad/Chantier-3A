"""Public pass reference format TDEV-YYYY-NNNN."""

from __future__ import annotations

import re

REF_PATTERN = re.compile(r"^TDEV-\d{4}-\d{4}$")


def format_pass_ref(year: int, seq: int) -> str:
    """Format a sequential public pass reference for the given calendar year."""
    return f"TDEV-{year}-{seq:04d}"
