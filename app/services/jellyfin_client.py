from __future__ import annotations

import time
from urllib.parse import urlsplit

import httpx

from app.diagnostics import log_diagnostic

_DEVICE_NAME = "JellyfinPosterManager"
_DEVICE_ID = "jellyfin-poster-mgr-001"
_CLIENT_NAME = "JellyfinPosterManager"
_CLIENT_VERSION = "1.0.0"


def _auth_header(token: str | None = None) -> str:
    base = (
        f'MediaBrowser Client="{_CLIENT_NAME}", '
        f'Device="{_DEVICE_NAME}", '
        f'DeviceId="{_DEVICE_ID}", '
        f'Version="{_CLIENT_VERSION}"'
    )
    if token:
        base += f', Token="{token}"'
    return base


class JellyfinClient:
    def __init__(self, server_url: str) -> None:
        self.server_url = server_url.rstrip("/")
        self.token: str | None = None
        self.user_id: str | None = None
        self._active_proxy_requests = 0
        self._http = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        )

    def _pool_snapshot(self) -> dict[str, int | None]:
        """Best-effort diagnostics only; never affects request behavior."""
        try:
            pool = getattr(getattr(self._http, "_transport", None), "_pool", None)
            connections = getattr(pool, "connections", None)
            if connections is None:
                return {"pool_connections": None, "pool_available": None}
            return {
                "pool_connections": len(connections),
                "pool_available": sum(1 for connection in connections if connection.is_available()),
            }
        except Exception:
            return {"pool_connections": None, "pool_available": None}

    async def close(self) -> None:
        await self._http.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "X-Emby-Authorization": _auth_header(self.token),
        }

    async def authenticate(self, username: str, password: str) -> dict:
        resp = await self._http.post(
            f"{self.server_url}/Users/AuthenticateByName",
            json={"Username": username, "Pw": password},
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data["AccessToken"]
        self.user_id = data["User"]["Id"]
        return {"user_id": self.user_id, "server_name": data["User"].get("ServerName", "")}

    @property
    def is_authenticated(self) -> bool:
        return self.token is not None and self.user_id is not None

    async def get_movies(self) -> list[dict]:
        started_at = time.perf_counter()
        log_diagnostic(
            "jellyfin.movies.start",
            active_proxy_requests=self._active_proxy_requests,
            **self._pool_snapshot(),
        )
        try:
            resp = await self._http.get(
                f"{self.server_url}/Users/{self.user_id}/Items",
                params={
                    "IncludeItemTypes": "Movie",
                    "Recursive": "true",
                    "SortBy": "SortName",
                    "SortOrder": "Ascending",
                    "Fields": "PrimaryImageAspectRatio,ImageTags,BackdropImageTags",
                    "EnableImageTypes": "Primary,Backdrop,Logo",
                    "Limit": "2000",
                },
                headers=self._headers(),
            )
        except Exception as error:
            log_diagnostic(
                "jellyfin.movies.error",
                error_type=type(error).__name__,
                elapsed_ms=round((time.perf_counter() - started_at) * 1000, 1),
                active_proxy_requests=self._active_proxy_requests,
                **self._pool_snapshot(),
            )
            raise
        resp.raise_for_status()
        data = resp.json()
        movies = []
        for item in data.get("Items", []):
            image_tags = item.get("ImageTags", {})
            backdrop_tags = item.get("BackdropImageTags", [])
            movies.append({
                "id": item["Id"],
                "name": item["Name"],
                "year": item.get("ProductionYear"),
                "has_poster": "Primary" in image_tags,
                "has_backdrop": len(backdrop_tags) > 0,
                "has_logo": "Logo" in image_tags,
            })
        log_diagnostic(
            "jellyfin.movies.complete",
            status=resp.status_code,
            movie_count=len(movies),
            elapsed_ms=round((time.perf_counter() - started_at) * 1000, 1),
            active_proxy_requests=self._active_proxy_requests,
            **self._pool_snapshot(),
        )
        return movies

    async def get_movie(self, item_id: str) -> dict:
        resp = await self._http.get(
            f"{self.server_url}/Users/{self.user_id}/Items/{item_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        item = resp.json()
        image_tags = item.get("ImageTags", {})
        backdrop_tags = item.get("BackdropImageTags", [])
        return {
            "id": item["Id"],
            "name": item["Name"],
            "year": item.get("ProductionYear"),
            "overview": item.get("Overview", ""),
            "has_poster": "Primary" in image_tags,
            "has_backdrop": len(backdrop_tags) > 0,
            "has_logo": "Logo" in image_tags,
        }

    def get_image_url(self, item_id: str, image_type: str, tag: str | None = None) -> str:
        url = f"{self.server_url}/Items/{item_id}/Images/{image_type}"
        if tag:
            url += f"?tag={tag}"
        return url

    async def get_current_images(self, item_id: str) -> dict:
        resp = await self._http.get(
            f"{self.server_url}/Users/{self.user_id}/Items/{item_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        item = resp.json()
        image_tags = item.get("ImageTags", {})
        backdrop_tags = item.get("BackdropImageTags", [])

        images = {}
        if "Primary" in image_tags:
            images["Primary"] = {
                "url": self.get_image_url(item_id, "Primary", image_tags["Primary"]),
                "tag": image_tags["Primary"],
            }
        if backdrop_tags:
            images["Backdrop"] = {
                "url": self.get_image_url(item_id, "Backdrop", backdrop_tags[0]),
                "tag": backdrop_tags[0],
            }
        if "Logo" in image_tags:
            images["Logo"] = {
                "url": self.get_image_url(item_id, "Logo", image_tags["Logo"]),
                "tag": image_tags["Logo"],
            }
        return images

    async def get_remote_images(self, item_id: str, image_type: str) -> list[dict]:
        resp = await self._http.get(
            f"{self.server_url}/Items/{item_id}/RemoteImages",
            params={"Type": image_type, "Limit": 30, "IncludeAllLanguages": "true"},
            headers=self._headers(),
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for img in data.get("Images", []):
            results.append({
                "url": img.get("Url", ""),
                "thumbnail_url": img.get("ThumbnailUrl") or img.get("Url", ""),
                "provider": img.get("ProviderName", "Unknown"),
                "width": img.get("Width"),
                "height": img.get("Height"),
                "language": img.get("Language"),
                "rating": img.get("CommunityRating"),
                "vote_count": img.get("VoteCount"),
                "type": image_type,
            })
        return results

    async def get_all_remote_images(self, item_id: str) -> dict:
        import asyncio
        started_at = time.perf_counter()
        log_diagnostic(
            "jellyfin.remote_images.start",
            item_id=item_id,
            active_proxy_requests=self._active_proxy_requests,
            **self._pool_snapshot(),
        )
        primary, backdrop, logo, thumb = await asyncio.gather(
            self.get_remote_images(item_id, "Primary"),
            self.get_remote_images(item_id, "Backdrop"),
            self.get_remote_images(item_id, "Logo"),
            self.get_remote_images(item_id, "Thumb"),
            return_exceptions=True,
        )
        backdrop_list = backdrop if not isinstance(backdrop, Exception) else []
        thumb_list = thumb if not isinstance(thumb, Exception) else []
        result = {
            "Primary": primary if not isinstance(primary, Exception) else [],
            "Backdrop": backdrop_list + thumb_list,
            "Logo": logo if not isinstance(logo, Exception) else [],
        }
        log_diagnostic(
            "jellyfin.remote_images.complete",
            item_id=item_id,
            elapsed_ms=round((time.perf_counter() - started_at) * 1000, 1),
            counts={image_type: len(images) for image_type, images in result.items()},
            errors=sum(isinstance(value, Exception) for value in (primary, backdrop, logo, thumb)),
            active_proxy_requests=self._active_proxy_requests,
            **self._pool_snapshot(),
        )
        return result

    async def delete_item_images(self, item_id: str, image_type: str) -> None:
        """Delete ALL images of the given type from the item."""
        resp = await self._http.get(
            f"{self.server_url}/Users/{self.user_id}/Items/{item_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        item = resp.json()

        if image_type == "Backdrop":
            count = len(item.get("BackdropImageTags", []))
        else:
            count = 1 if image_type in item.get("ImageTags", {}) else 0

        # Delete from highest index downward to avoid index shifting
        for i in range(count - 1, -1, -1):
            await self._http.delete(
                f"{self.server_url}/Items/{item_id}/Images/{image_type}/{i}",
                headers=self._headers(),
            )

    async def apply_remote_image(self, item_id: str, image_type: str, image_url: str) -> bool:
        resp = await self._http.post(
            f"{self.server_url}/Items/{item_id}/RemoteImages/Download",
            params={"Type": image_type, "ImageUrl": image_url},
            headers=self._headers(),
            timeout=30.0,
        )
        return resp.status_code in (200, 204)

    async def verify_image(self, item_id: str, image_type: str) -> bool:
        """Re-fetch the item and confirm the image type is present."""
        resp = await self._http.get(
            f"{self.server_url}/Users/{self.user_id}/Items/{item_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        item = resp.json()
        if image_type == "Backdrop":
            return len(item.get("BackdropImageTags", [])) > 0
        return image_type in item.get("ImageTags", {})

    async def proxy_image(self, url: str) -> tuple[bytes, str]:
        started_at = time.perf_counter()
        self._active_proxy_requests += 1
        upstream_host = urlsplit(url).hostname or "unknown"
        log_diagnostic(
            "jellyfin.proxy.start",
            upstream_host=upstream_host,
            active_proxy_requests=self._active_proxy_requests,
            **self._pool_snapshot(),
        )
        try:
            resp = await self._http.get(
                url,
                headers=self._headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            log_diagnostic(
                "jellyfin.proxy.complete",
                upstream_host=upstream_host,
                status=resp.status_code,
                bytes=len(resp.content),
                elapsed_ms=round((time.perf_counter() - started_at) * 1000, 1),
                active_proxy_requests=self._active_proxy_requests,
                **self._pool_snapshot(),
            )
            return resp.content, content_type
        except Exception as error:
            log_diagnostic(
                "jellyfin.proxy.error",
                upstream_host=upstream_host,
                error_type=type(error).__name__,
                elapsed_ms=round((time.perf_counter() - started_at) * 1000, 1),
                active_proxy_requests=self._active_proxy_requests,
                **self._pool_snapshot(),
            )
            raise
        finally:
            self._active_proxy_requests -= 1
