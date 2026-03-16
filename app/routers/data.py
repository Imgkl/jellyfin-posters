from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import require_auth
from app.models.schemas import ImportRequest
from app.services.progress_db import get_all_records, merge_records, replace_all_records
from app.state import AppState

router = APIRouter(prefix="/api/data")


@router.get("/export")
async def export_data(state: AppState = Depends(require_auth)):
    records = await get_all_records()

    # Backfill empty URLs from Jellyfin for reviewed items
    image_types = [
        ("poster_changed", "poster_url", "Primary"),
        ("backdrop_changed", "backdrop_url", "Backdrop"),
        ("logo_changed", "logo_url", "Logo"),
    ]
    for rec in records:
        needs_backfill = any(
            rec.get(changed) and not rec.get(url_key)
            for changed, url_key, _ in image_types
        )
        if needs_backfill:
            try:
                current = await state.client.get_current_images(rec["item_id"])
                for changed, url_key, jf_type in image_types:
                    if rec.get(changed) and not rec.get(url_key) and jf_type in current:
                        rec[url_key] = current[jf_type]["url"]
            except Exception:
                pass  # Skip if item no longer exists

    return {
        "version": "1.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "server_url": state.client.server_url,
        "record_count": len(records),
        "records": records,
    }


@router.post("/import")
async def import_data(req: ImportRequest, _state: AppState = Depends(require_auth)):
    if req.mode == "replace":
        count = await replace_all_records(req.records)
    else:
        count = await merge_records(req.records)
    return {"ok": True, "imported": count, "mode": req.mode}
