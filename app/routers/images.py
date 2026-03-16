from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.dependencies import require_auth
from app.models.schemas import ApplyImageRequest
from app.state import AppState

router = APIRouter()


@router.get("/api/movies/{item_id}/images")
async def get_current_images(item_id: str, state: AppState = Depends(require_auth)):
    images = await state.client.get_current_images(item_id)
    for img_type, info in images.items():
        info["proxy_url"] = f"/api/proxy-image?url={info['url']}"
    return images


@router.get("/api/movies/{item_id}/remote-images")
async def get_remote_images(item_id: str, type: str | None = None, state: AppState = Depends(require_auth)):
    all_images = await state.get_remote_images_cached(item_id)
    if type:
        return {"images": all_images.get(type, []), "type": type}
    return all_images


@router.post("/api/movies/{item_id}/apply-image")
async def apply_image(item_id: str, req: ApplyImageRequest, state: AppState = Depends(require_auth)):
    if req.type == "Backdrop":
        await state.client.delete_item_images(item_id, "Backdrop")
    ok = await state.client.apply_remote_image(item_id, req.type, req.url)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to apply image")
    verified = await state.client.verify_image(item_id, req.type)
    if not verified:
        raise HTTPException(status_code=500, detail=f"{req.type} was not saved by Jellyfin")
    return {"ok": True}


@router.get("/api/proxy-image")
async def proxy_image(url: str, state: AppState = Depends(require_auth)):
    try:
        content, content_type = await state.client.proxy_image(url)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch image")
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
