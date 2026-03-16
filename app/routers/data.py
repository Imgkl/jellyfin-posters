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
