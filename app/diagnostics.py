from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from typing import Any

_logger = logging.getLogger("uvicorn.error")
request_id_var: ContextVar[str] = ContextVar("jp_diagnostic_request_id", default="-")


def log_diagnostic(event: str, **fields: Any) -> None:
    """Emit one structured diagnostic event without request bodies or URLs."""
    record = {
        "event": event,
        "request_id": request_id_var.get(),
        **fields,
    }
    _logger.info("[JP-DIAG] %s", json.dumps(record, sort_keys=True, default=str))
