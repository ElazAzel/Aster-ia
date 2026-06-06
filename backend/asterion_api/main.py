from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from asterion_api.config import get_settings
from asterion_api.dependencies import get_ollama_service, get_store
from asterion_api.routers import (
    agents,
    analytics,
    artifacts,
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
    workflows,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await get_store().ensure_schema()
    # Auto-pull required models (graceful — does not block if Ollama is offline)
    ollama = get_ollama_service()
    await ollama.ensure_models(settings.required_models)
    yield
    await ollama.aclose()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

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
