"""Placeholder for optional stub routes; documented API surface lives in sibling route modules."""

from __future__ import annotations

from fastapi import APIRouter

_STUBS: list[tuple[str, str]] = []


def register_stubs(api: APIRouter) -> None:
    """Register stubs."""
    del api
    for _method, _path in _STUBS:
        pass
