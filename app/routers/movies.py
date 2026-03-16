from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import require_auth
from app.services.progress_db import get_reviewed_ids
from app.state import AppState

router = APIRouter(prefix="/api/movies")


@router.get("")
async def list_movies(state: AppState = Depends(require_auth)):
    reviewed = await get_reviewed_ids()
    for i, m in enumerate(state.movie_list):
        m["index"] = i
        m["reviewed"] = m["id"] in reviewed
    return {"items": state.movie_list, "total": len(state.movie_list)}


@router.get("/{item_id}")
async def get_movie(item_id: str, state: AppState = Depends(require_auth)):
    try:
        movie = await state.client.get_movie(item_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    reviewed = await get_reviewed_ids()
    movie["reviewed"] = item_id in reviewed
    return movie
