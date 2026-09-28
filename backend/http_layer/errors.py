"""JSON error shape and FastAPI handlers shared by HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

CODE_INVALID = "invalid_request"
CODE_UNAUTHORIZED = "unauthorized"
CODE_FORBIDDEN = "forbidden"
CODE_NOT_FOUND = "not_found"
CODE_CONFLICT = "conflict"
CODE_RATE_LIMITED = "rate_limited"
CODE_INTERNAL = "internal_error"
CODE_NOT_IMPLEMENTED = "not_implemented"


def error_body(code: str, message: str) -> dict[str, Any]:
    """Error body."""
    return {"error": {"code": code, "message": message}}


def json_error(status: int, code: str, message: str) -> JSONResponse:
    """Json error."""
    return JSONResponse(status_code=status, content=error_body(code, message))


async def not_implemented_handler(_request: Request) -> JSONResponse:
    """Not implemented handler."""
    return json_error(
        501,
        CODE_NOT_IMPLEMENTED,
        "This route is not implemented in the Python backend; use the Go server instead.",
    )
