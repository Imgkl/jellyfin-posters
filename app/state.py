from __future__ import annotations

import time

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
                return data
        data = await self.client.get_all_remote_images(item_id)
        self.remote_cache[item_id] = (now, data)
        return data

    async def replace_client(self, new_url: str) -> None:
        await self.client.close()
        self.client = JellyfinClient(new_url)
