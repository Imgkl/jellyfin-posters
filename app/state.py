from __future__ import annotations

import time

from app.diagnostics import log_diagnostic
from app.services.jellyfin_client import JellyfinClient


class AppState:
    def __init__(self, server_url: str) -> None:
        self.client = JellyfinClient(server_url)
        self.movie_list: list[dict] = []
        self.remote_cache: dict[str, tuple[float, dict]] = {}
        self.cache_ttl: int = 600  # 10 minutes

    async def close(self) -> None:
        await self.client.close()

    async def get_remote_images_cached(self, item_id: str) -> dict:
        now = time.time()
        if item_id in self.remote_cache:
            ts, data = self.remote_cache[item_id]
            if now - ts < self.cache_ttl:
                log_diagnostic(
                    "remote_cache.hit",
                    item_id=item_id,
                    age_ms=round((now - ts) * 1000, 1),
                    cache_entries=len(self.remote_cache),
                )
                return data
        log_diagnostic("remote_cache.miss", item_id=item_id, cache_entries=len(self.remote_cache))
        data = await self.client.get_all_remote_images(item_id)
        self.remote_cache[item_id] = (now, data)
        log_diagnostic("remote_cache.stored", item_id=item_id, cache_entries=len(self.remote_cache))
        return data

    async def replace_client(self, new_url: str) -> None:
        await self.client.close()
        self.client = JellyfinClient(new_url)
