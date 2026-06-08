from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from asterion_api.config import get_settings
from asterion_api.dependencies import get_document_indexer, get_store
from asterion_api.exceptions import AsterionAPIError, global_exception_handler
from asterion_api.routers import (
    agents,
    analytics,
    artifacts,
    audit,
    benchmark,
    chat,
    export,
    health,
    images,
    memory,
    models,
    plugins,
    privacy,
    rag,
    research,
    rooms,
    system,
    telemetry,
    voice,
    workflows,
)

# In-Memory Rate Limiting
RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_ENTRIES = 10_000
request_history: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=RATE_LIMIT_REQUESTS * 2))


async def memory_ttl_enforcer() -> None:
    """Background task to automatically expire memories based on expires_at."""
    store = get_store()
    while True:
        try:
            count = await store.expire_memories()
            if count > 0:
                # Structured logs are managed by store, but we can print here
                pass
        except Exception:
            pass
        await asyncio.sleep(600)  # Check every 10 minutes


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await get_store().ensure_schema()
    await get_document_indexer().start_watching()
    yield
    get_document_indexer().stop_watching()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(AsterionAPIError, global_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://tauri.localhost",
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Response:
    response: Response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' ws://127.0.0.1:* ws://localhost:* http://127.0.0.1:* http://localhost:*; "
        "img-src 'self' data: http://127.0.0.1:* http://localhost:*; "
        "frame-ancestors 'none';"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# Periodic cleanup of stale IPs from rate limiter
_RATE_LIMIT_LAST_CLEANUP = time.time()


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next: Any) -> Response:
    global _RATE_LIMIT_LAST_CLEANUP
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    
    history = request_history[client_ip]
    # Prune expired entries
    while history and history[0] < now - RATE_LIMIT_WINDOW_SECONDS:
        history.popleft()
        
    if len(history) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests. Rate limit exceeded."},
        )
        
    history.append(now)

    # Periodically purge stale IPs to avoid memory leak
    if now - _RATE_LIMIT_LAST_CLEANUP > 300:
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        stale_ips = [ip for ip, h in request_history.items() if not h or h[-1] < cutoff]
        for ip in stale_ips:
            del request_history[ip]
        _RATE_LIMIT_LAST_CLEANUP = now
    
    return await call_next(request)


app.include_router(health.router)
app.include_router(models.router)
app.include_router(chat.router)
app.include_router(privacy.router)
app.include_router(rooms.router)
app.include_router(memory.router)
app.include_router(rag.router)
app.include_router(research.router)
app.include_router(agents.router)
app.include_router(artifacts.router)
app.include_router(images.router)
app.include_router(workflows.router)
app.include_router(plugins.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(benchmark.router)
app.include_router(export.router)
app.include_router(system.router)
app.include_router(telemetry.router)
app.include_router(voice.router)
