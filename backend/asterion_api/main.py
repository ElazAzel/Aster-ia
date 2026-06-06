from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from asterion_api.config import get_settings
from asterion_api.dependencies import get_document_indexer, get_ollama_service, get_store
from asterion_api.exceptions import AsterionAPIError, global_exception_handler
from asterion_api.routers import (
    agents,
    analytics,
    artifacts,
    audit,
    chat,
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
    workflows,
)

# In-Memory Rate Limiting
RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60
request_history: dict[str, list[float]] = defaultdict(list)


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
    settings = get_settings()
    await get_store().ensure_schema()
    
    # Auto-pull required models (graceful — does not block if Ollama is offline)
    ollama = get_ollama_service()
    await ollama.ensure_models(settings.required_models)
    
    # Start RAG file watcher
    indexer = get_document_indexer()
    indexer.start_watcher(watch_dir=settings.data_dir / "vault")
    
    # Start memory TTL enforcer
    ttl_task = asyncio.create_task(memory_ttl_enforcer())
    
    yield
    
    # Cancel memory TTL enforcer
    ttl_task.cancel()
    try:
        await ttl_task
    except asyncio.CancelledError:
        pass
        
    await ollama.aclose()


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
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
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


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next: Any) -> Response:
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    
    history = request_history[client_ip]
    while history and history[0] < now - RATE_LIMIT_WINDOW_SECONDS:
        history.pop(0)
        
    if len(history) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests. Rate limit exceeded."},
        )
        
    history.append(now)
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
app.include_router(system.router)
app.include_router(telemetry.router)
