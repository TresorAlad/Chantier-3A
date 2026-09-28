"""Serve uploaded event media files."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from http_layer.deps import AppState, get_app_state
from http_layer.errors import json_error

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{media_id}")
def serve_media(media_id: str, state: AppState = Depends(get_app_state)):
    """Serve media."""
    if not media_id or "/" in media_id or ".." in media_id:
        return json_error(400, "invalid_request", "invalid media id")
    base = Path(state.config.media_dir).resolve()
    for suffix in ("", ".jpg", ".jpeg", ".png", ".webp"):
        path = (base / f"{media_id}{suffix}").resolve()
        if not str(path).startswith(str(base)):
            continue
        if path.is_file():
            return FileResponse(path)
    return json_error(404, "not_found", "media not found")
