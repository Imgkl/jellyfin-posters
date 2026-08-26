from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, data, images, library, movies, progress
from app.services.progress_db import init_db
from app.state import AppState

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState(settings.jellyfin_url)
    app.state.app_state = state
    await init_db()
    yield
    await state.close()


app = FastAPI(lifespan=lifespan)

# Routers
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(images.router)
app.include_router(library.router)
app.include_router(progress.router)
app.include_router(data.router)

# Static files
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# SPA fallback
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    with open(_STATIC_DIR / "index.html") as f:
        return HTMLResponse(f.read())
