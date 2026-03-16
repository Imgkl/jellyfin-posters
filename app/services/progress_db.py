from __future__ import annotations

import aiosqlite

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS progress (
    item_id TEXT PRIMARY KEY,
    item_name TEXT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    poster_changed BOOLEAN DEFAULT 0,
    backdrop_changed BOOLEAN DEFAULT 0,
    logo_changed BOOLEAN DEFAULT 0,
    poster_url TEXT DEFAULT '',
    backdrop_url TEXT DEFAULT '',
    logo_url TEXT DEFAULT ''
);
"""

_MIGRATE_COLUMNS = [
    ("poster_url", "TEXT DEFAULT ''"),
    ("backdrop_url", "TEXT DEFAULT ''"),
    ("logo_url", "TEXT DEFAULT ''"),
]


async def init_db() -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(_SCHEMA)
        # Migrate: add url columns if missing (existing DBs)
        cursor = await db.execute("PRAGMA table_info(progress)")
        existing = {row[1] for row in await cursor.fetchall()}
        for col, typedef in _MIGRATE_COLUMNS:
            if col not in existing:
                await db.execute(f"ALTER TABLE progress ADD COLUMN {col} {typedef}")
        await db.commit()


async def mark_reviewed(
    item_id: str,
    item_name: str,
    poster_changed: bool = False,
    backdrop_changed: bool = False,
    logo_changed: bool = False,
    poster_url: str = "",
    backdrop_url: str = "",
    logo_url: str = "",
) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """INSERT INTO progress (item_id, item_name, poster_changed, backdrop_changed, logo_changed, poster_url, backdrop_url, logo_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(item_id) DO UPDATE SET
                   reviewed_at = CURRENT_TIMESTAMP,
                   poster_changed = excluded.poster_changed,
                   backdrop_changed = excluded.backdrop_changed,
                   logo_changed = excluded.logo_changed,
                   poster_url = excluded.poster_url,
                   backdrop_url = excluded.backdrop_url,
                   logo_url = excluded.logo_url
            """,
            (item_id, item_name, poster_changed, backdrop_changed, logo_changed, poster_url, backdrop_url, logo_url),
        )
        await db.commit()


async def get_reviewed_ids() -> set[str]:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute("SELECT item_id FROM progress")
        rows = await cursor.fetchall()
        return {row[0] for row in rows}


async def cleanup_removed(valid_ids: set[str]) -> int:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute("SELECT item_id FROM progress")
        rows = await cursor.fetchall()
        stale = [row[0] for row in rows if row[0] not in valid_ids]
        if stale:
            placeholders = ",".join("?" for _ in stale)
            await db.execute(
                f"DELETE FROM progress WHERE item_id IN ({placeholders})", stale
            )
            await db.commit()
        return len(stale)


async def get_stats() -> dict:
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM progress")
        row = await cursor.fetchone()
        return {"reviewed": row[0] if row else 0}


async def get_all_records() -> list[dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM progress")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def merge_records(records: list[dict]) -> int:
    count = 0
    async with aiosqlite.connect(settings.db_path) as db:
        for r in records:
            await db.execute(
                """INSERT INTO progress (item_id, item_name, reviewed_at, poster_changed, backdrop_changed, logo_changed, poster_url, backdrop_url, logo_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(item_id) DO UPDATE SET
                       item_name = excluded.item_name,
                       reviewed_at = excluded.reviewed_at,
                       poster_changed = excluded.poster_changed,
                       backdrop_changed = excluded.backdrop_changed,
                       logo_changed = excluded.logo_changed,
                       poster_url = excluded.poster_url,
                       backdrop_url = excluded.backdrop_url,
                       logo_url = excluded.logo_url
                """,
                (
                    r["item_id"],
                    r.get("item_name", ""),
                    r.get("reviewed_at"),
                    r.get("poster_changed", False),
                    r.get("backdrop_changed", False),
                    r.get("logo_changed", False),
                    r.get("poster_url", ""),
                    r.get("backdrop_url", ""),
                    r.get("logo_url", ""),
                ),
            )
            count += 1
        await db.commit()
    return count


async def replace_all_records(records: list[dict]) -> int:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("DELETE FROM progress")
        count = 0
        for r in records:
            await db.execute(
                """INSERT INTO progress (item_id, item_name, reviewed_at, poster_changed, backdrop_changed, logo_changed, poster_url, backdrop_url, logo_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["item_id"],
                    r.get("item_name", ""),
                    r.get("reviewed_at"),
                    r.get("poster_changed", False),
                    r.get("backdrop_changed", False),
                    r.get("logo_changed", False),
                    r.get("poster_url", ""),
                    r.get("backdrop_url", ""),
                    r.get("logo_url", ""),
                ),
            )
            count += 1
        await db.commit()
    return count
