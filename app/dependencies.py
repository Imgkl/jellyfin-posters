from __future__ import annotations

from fastapi import HTTPException, Request

from app.state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


def require_auth(request: Request) -> AppState:
    state: AppState = request.app.state.app_state
    if not state.client.is_authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return state
