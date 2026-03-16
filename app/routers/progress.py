from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import require_auth
from app.services.progress_db import get_stats
from app.state import AppState

router = APIRouter(prefix="/api/progress")


@router.get("")
async def progress(state: AppState = Depends(require_auth)):
    stats = await get_stats()
    stats["total"] = len(state.movie_list)
    stats["pending"] = stats["total"] - stats["reviewed"]
    return stats
