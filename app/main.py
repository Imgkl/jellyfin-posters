from __future__ import annotations

import time
import uuid
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.diagnostics import log_diagnostic, request_id_var
from app.routers import auth, data, images, library, movies, progress
from app.services.progress_db import init_db
from app.state import AppState

_STATIC_DIR = Path(__file__).parent / "static"
_active_api_requests = 0
_BROWSER_DIAGNOSTIC_ID = re.compile(r"^web-[a-z0-9]{8,16}-[a-z0-9]{6}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState(settings.jellyfin_url)
    app.state.app_state = state
    await init_db()
    yield
    await state.close()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def diagnostic_request_timing(request: Request, call_next):
    """Correlate browser API timing with server receipt without logging queries or bodies."""
    global _active_api_requests
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    supplied_request_id = request.headers.get("X-JP-Diagnostic-ID", "")
    request_id = (
        supplied_request_id
        if _BROWSER_DIAGNOSTIC_ID.fullmatch(supplied_request_id)
        else f"server-{uuid.uuid4().hex[:12]}"
    )
    token = request_id_var.set(request_id)
    started_at = time.perf_counter()
    _active_api_requests += 1
    log_diagnostic(
        "request.start",
        method=request.method,
        path=request.url.path,
        active_api_requests=_active_api_requests,
    )
    try:
        response = await call_next(request)
        response.headers["X-JP-Diagnostic-ID"] = request_id
        log_diagnostic(
            "request.complete",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=round((time.perf_counter() - started_at) * 1000, 1),
            active_api_requests=_active_api_requests,
        )
        return response
    except Exception as error:
        log_diagnostic(
            "request.error",
            method=request.method,
            path=request.url.path,
            error_type=type(error).__name__,
            elapsed_ms=round((time.perf_counter() - started_at) * 1000, 1),
            active_api_requests=_active_api_requests,
        )
        raise
    finally:
        _active_api_requests -= 1
        request_id_var.reset(token)

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
