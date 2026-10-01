"""Pydantic request/response models of the check-in API (OpenAPI is generated from these)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class ScanRequest(_Strict):
    """Online scan of one QR presented at a station."""

    event_id: str = Field(min_length=1, max_length=64)
    terminal_id: UUID
    station: str = Field(min_length=1, max_length=40, description="EVENT_ENTRY, FOOD_ACCESS, ...")
    capability: str = Field(min_length=1, max_length=4096, description="QR content; never stored or logged")
    operation_id: UUID | None = Field(default=None, description="Idempotency key (recommended)")
    scanned_at: datetime | None = None
    app_version: str = Field(default="", max_length=64)


class ScanResponse(BaseModel):
    """Outcome of an online scan."""

    status: Literal["accepted", "conflict", "already_processed"]
    server_decision: str
    reason: str = ""
    ticket_id: str = ""
    serial: str = ""
    station: str
    use_index: int | None = None
    first_scanned_at: datetime | None = None
    operation_id: UUID


class SyncOperation(_Strict):
    """One offline operation, as written by the 3B outbox (plus the fields to add)."""

    operation_id: UUID
    scan_id: UUID | None = None
    ticket_id: str | None = Field(default=None, max_length=64)
    participant_id: str | None = Field(default=None, max_length=64)
    station: str = Field(min_length=1, max_length=40)
    decision: str = Field(min_length=1, max_length=40)
    evaluated_at: datetime
    previous_scan_at: datetime | None = None
    qr_version: int | None = None
    staff_id: str | None = Field(default=None, max_length=64)
    capability: str | None = Field(default=None, max_length=4096, description="Optional; never stored")


class SyncRequest(_Strict):
    """Batch of offline operations."""

    event_id: str = Field(min_length=1, max_length=64)
    terminal_id: UUID
    batch_id: UUID
    device_sent_at: datetime
    app_version: str = Field(default="", max_length=64)
    pending_count: int | None = Field(default=None, ge=0)
    operations: list[Any] = Field(description="Validated one by one: a bad item never fails the batch")


class AcknowledgeRequest(_Strict):
    """Supervisor acknowledgement of a conflict."""

    note: str = Field(default="", max_length=1000)
