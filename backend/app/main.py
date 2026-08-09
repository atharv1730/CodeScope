"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analyses, health

app = FastAPI(
    title="RepoLens API",
    version="0.1.0",
    description="Clone a public GitHub repo and generate a codebase health report.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyses.router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"service": "RepoLens API", "docs": "/docs"}
