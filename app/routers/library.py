from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from app.dependencies import require_auth
from app.models.schemas import MarkReviewedRequest
from app.services.progress_db import cleanup_removed, mark_reviewed
from app.state import AppState

router = APIRouter()


@router.post("/api/library/refresh")
async def refresh_movies(state: AppState = Depends(require_auth)):
    state.movie_list = await state.client.get_movies()
    state.remote_cache.clear()
    valid_ids = {m["id"] for m in state.movie_list}
    removed = await cleanup_removed(valid_ids)
    return {"ok": True, "total_movies": len(state.movie_list), "stale_removed": removed}


@router.post("/api/library/cleanup-backdrops")
async def cleanup_backdrops(state: AppState = Depends(require_auth)):
    fixed = 0
    for movie in state.movie_list:
        item_id = movie["id"]
        resp = await state.client._http.get(
            f"{state.client.server_url}/Users/{state.client.user_id}/Items/{item_id}",
            headers=state.client._headers(),
        )
        resp.raise_for_status()
        tags = resp.json().get("BackdropImageTags", [])
        if len(tags) > 1:
            for i in range(len(tags) - 1, 0, -1):
                await state.client._http.delete(
                    f"{state.client.server_url}/Items/{item_id}/Images/Backdrop/{i}",
                    headers=state.client._headers(),
                )
            fixed += 1
    return {"ok": True, "fixed": fixed}


@router.post("/api/movies/{item_id}/prefetch")
async def prefetch(item_id: str, state: AppState = Depends(require_auth)):
    """Fire-and-forget prefetch of remote images for a movie."""
    asyncio.create_task(state.get_remote_images_cached(item_id))
    return {"ok": True}


@router.post("/api/movies/{item_id}/mark-reviewed")
async def mark_movie_reviewed(item_id: str, req: MarkReviewedRequest, state: AppState = Depends(require_auth)):
    name = ""
    for m in state.movie_list:
        if m["id"] == item_id:
            name = m["name"]
            break
    await mark_reviewed(
        item_id, name,
        req.poster_changed, req.backdrop_changed, req.logo_changed,
        req.poster_url, req.backdrop_url, req.logo_url,
    )
    return {"ok": True}
