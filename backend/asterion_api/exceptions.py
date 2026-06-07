from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from asterion_api.structured_logging import StructuredLogger

logger = StructuredLogger("api.exceptions", "local")


class AsterionAPIError(Exception):
    """Base exception for Asterion API errors."""

    def __init__(self, message: str, code: str = "internal_error", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    headers = {}
    origin = request.headers.get("origin")
    allowed_origins = {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://tauri.localhost",
        "tauri://localhost",
    }
    if origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    if isinstance(exc, AsterionAPIError):
        logger.emit(
            "api.error",
            error=exc.message,
            code=exc.code,
            status=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "code": exc.code},
            headers=headers,
        )

    # Unhandled exceptions
    logger.emit(
        "api.unhandled_error",
        error=str(exc),
        path=request.url.path,
        type=exc.__class__.__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected internal server error occurred.", "code": "internal_error"},
        headers=headers,
    )
