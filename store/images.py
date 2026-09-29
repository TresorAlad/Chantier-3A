"""Event image metadata and on-disk media paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from store.store import NotFoundError, Store, new_ulid
from store.timeutil import time_to_text, text_to_time


@dataclass
class Image:
    """Image."""
    id: str
    event_id: str
    format: str
    width: int
    height: int
    size_bytes: int
    uploaded_by: str | None
    created_at: datetime


def create_image(st: Store, img: Image) -> None:
    """Create image."""
    if not img.id:
        img.id = new_ulid()
    st.execute(
        """
        INSERT INTO images (id, event_id, format, width, height, size_bytes, uploaded_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            img.id,
            img.event_id,
            img.format,
            img.width,
            img.height,
            img.size_bytes,
            img.uploaded_by,
            time_to_text(img.created_at),
        ),
    )


def get_image(st: Store, image_id: str) -> Image:
    """Get image."""
    row = st.fetchone(
        """
        SELECT id, event_id, format, width, height, size_bytes, uploaded_by, created_at
        FROM images WHERE id = ?
        """,
        (image_id,),
    )
    if row is None:
        raise NotFoundError()
    return _row_image(row)


def image_event_id(st: Store, image_id: str) -> str:
    """Image event id."""
    row = st.fetchone("SELECT event_id FROM images WHERE id = ?", (image_id,))
    if row is None:
        raise NotFoundError()
    return row["event_id"] if hasattr(row, "keys") else row[0]


def delete_image(st: Store, image_id: str) -> None:
    """Delete image."""
    st.execute("DELETE FROM images WHERE id = ?", (image_id,))


def list_images_by_event(st: Store, event_id: str) -> list[Image]:
    """List images by event."""
    rows = st.fetchall(
        """
        SELECT id, event_id, format, width, height, size_bytes, uploaded_by, created_at
        FROM images WHERE event_id = ? ORDER BY created_at ASC, id ASC
        """,
        (event_id,),
    )
    return [_row_image(r) for r in rows]


def _row_image(row) -> Image:
    """Internal: row image."""
    if hasattr(row, "keys"):
        ub = row["uploaded_by"]
        return Image(
            id=row["id"],
            event_id=row["event_id"],
            format=row["format"],
            width=int(row["width"]),
            height=int(row["height"]),
            size_bytes=int(row["size_bytes"]),
            uploaded_by=ub,
            created_at=text_to_time(row["created_at"]),
        )
    return Image(
        id=row[0],
        event_id=row[1],
        format=row[2],
        width=int(row[3]),
        height=int(row[4]),
        size_bytes=int(row[5]),
        uploaded_by=row[6],
        created_at=text_to_time(row[7]),
    )
