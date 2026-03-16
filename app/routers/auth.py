from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.dependencies import get_state
from app.models.schemas import LoginRequest
from app.state import AppState

router = APIRouter(prefix="/api/auth")


@router.post("/login")
async def login(req: LoginRequest, state: AppState = Depends(get_state)):
    # Substitute defaults from settings when fields are empty
    server_url = req.server_url.strip() or settings.jellyfin_url
    username = req.username.strip() or settings.jellyfin_username
    password = req.password or settings.jellyfin_password

    url = server_url.rstrip("/")
    if url != state.client.server_url:
        await state.replace_client(url)

    try:
        result = await state.client.authenticate(username, password)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    state.movie_list = await state.client.get_movies()
    return {"ok": True, "user_id": result["user_id"], "total_movies": len(state.movie_list)}


@router.post("/logout")
async def logout(state: AppState = Depends(get_state)):
    server_url = state.client.server_url
    await state.client.close()
    from app.services.jellyfin_client import JellyfinClient
    state.client = JellyfinClient(server_url)
    state.movie_list = []
    state.remote_cache = {}
    return {"ok": True}


@router.get("/status")
async def auth_status(state: AppState = Depends(get_state)):
    has_default_credentials = bool(settings.jellyfin_username and settings.jellyfin_password)
    return {
        "authenticated": state.client.is_authenticated,
        "total_movies": len(state.movie_list),
        "default_server_url": settings.jellyfin_url,
        "default_username": settings.jellyfin_username,
        "has_default_credentials": has_default_credentials,
    }
