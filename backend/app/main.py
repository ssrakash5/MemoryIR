from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from .api import consolidate, demo, evaluation, forensics, interventions, memories, query, traces
from .config import get_settings
from .services.container import build_services

settings = get_settings()

app = FastAPI(
    title="MemoryIR",
    description="Forensics for persistent AI memory.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.state.services = build_services(settings)

app.include_router(memories.router, prefix="/api")
app.include_router(consolidate.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(traces.router, prefix="/api")
app.include_router(interventions.router, prefix="/api")
app.include_router(forensics.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "provider": settings.provider,
        "database_backend": settings.database_backend,
    }


dist_path = settings.frontend_dist_path
assets_path = dist_path / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def serve_spa(path: str = ""):
    requested = (dist_path / path).resolve()
    try:
        requested.relative_to(dist_path.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404) from exc
    if requested.is_file():
        return FileResponse(requested)
    index = dist_path / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(
        status_code=404,
        detail="Frontend build not found. Run `npm run build` in frontend and copy dist to backend/static.",
    )


handler = Mangum(app)
