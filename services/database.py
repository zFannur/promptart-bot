from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite
from loguru import logger

from config import settings
from utils.aspect_ratios import DEFAULT_RATIO
from utils.models import DEFAULT_EDIT_MODEL, DEFAULT_MODEL, LEGACY_MODEL_REMAP


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    language TEXT DEFAULT 'en',
    model TEXT DEFAULT 'flux',
    edit_model TEXT DEFAULT 'klein',
    aspect_ratio TEXT DEFAULT '1:1',
    style TEXT,
    tier TEXT DEFAULT 'free',
    quota_used INTEGER DEFAULT 0,
    quota_reset_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    video_model TEXT DEFAULT 'ltx-2',
    video_aspect_ratio TEXT DEFAULT '16:9',
    video_duration INTEGER DEFAULT 5,
    audio_model TEXT DEFAULT 'openai-audio',
    audio_voice TEXT DEFAULT 'nova',
    text_model TEXT DEFAULT 'openai',
    image_quality TEXT DEFAULT 'medium',
    image_transparent INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_users_tg ON users(telegram_id);

CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    enhanced_prompt TEXT,
    model TEXT NOT NULL,
    aspect_ratio TEXT NOT NULL,
    style TEXT,
    seed INTEGER,
    file_id TEXT,
    kind TEXT DEFAULT 'create',         -- 'create' | 'edit'
    source_photos TEXT,                 -- JSON list of telegram file_ids used as input (edits only)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_generations_user ON generations(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    generation_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, generation_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (generation_id) REFERENCES generations(id)
);
"""


@dataclass
class User:
    id: int
    telegram_id: int
    username: str | None
    language: str
    model: str
    edit_model: str
    aspect_ratio: str
    style: str | None
    tier: str
    video_model: str = 'ltx-2'
    video_aspect_ratio: str = '16:9'
    video_duration: int = 5
    audio_model: str = 'openai-audio'
    audio_voice: str = 'nova'
    text_model: str = 'openai'
    image_quality: str = 'medium'
    image_transparent: int = 0


@dataclass
class Generation:
    id: int
    user_id: int
    prompt: str
    enhanced_prompt: str | None
    model: str
    aspect_ratio: str
    style: str | None
    seed: int | None
    file_id: str | None
    kind: str = "create"  # 'create' | 'edit'
    source_photos: tuple[str, ...] = ()  # input file_ids for edits


def _row_to_user(row: aiosqlite.Row) -> User:
    keys = row.keys()
    edit_model = row["edit_model"] if "edit_model" in keys else DEFAULT_EDIT_MODEL
    video_model = row["video_model"] if "video_model" in keys else "ltx-2"
    video_aspect_ratio = row["video_aspect_ratio"] if "video_aspect_ratio" in keys else "16:9"
    video_duration = row["video_duration"] if "video_duration" in keys else 5
    audio_model = row["audio_model"] if "audio_model" in keys else "openai-audio"
    audio_voice = row["audio_voice"] if "audio_voice" in keys else "nova"
    text_model = row["text_model"] if "text_model" in keys else "openai"
    image_quality = row["image_quality"] if "image_quality" in keys else "medium"
    image_transparent = row["image_transparent"] if "image_transparent" in keys else 0
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        username=row["username"],
        language=row["language"],
        model=row["model"],
        edit_model=edit_model or DEFAULT_EDIT_MODEL,
        aspect_ratio=row["aspect_ratio"],
        style=row["style"],
        tier=row["tier"],
        video_model=video_model,
        video_aspect_ratio=video_aspect_ratio,
        video_duration=video_duration,
        audio_model=audio_model,
        audio_voice=audio_voice,
        text_model=text_model,
        image_quality=image_quality,
        image_transparent=image_transparent,
    )


def _row_to_gen(row: aiosqlite.Row) -> Generation:
    keys = row.keys()
    kind = row["kind"] if "kind" in keys else "create"
    raw_sources = row["source_photos"] if "source_photos" in keys else None
    source_photos: tuple[str, ...] = ()
    if raw_sources:
        try:
            parsed = json.loads(raw_sources)
            if isinstance(parsed, list):
                source_photos = tuple(str(x) for x in parsed)
        except (TypeError, ValueError):
            logger.warning("gen {} has malformed source_photos JSON", row["id"])
    return Generation(
        id=row["id"],
        user_id=row["user_id"],
        prompt=row["prompt"],
        enhanced_prompt=row["enhanced_prompt"],
        model=row["model"],
        aspect_ratio=row["aspect_ratio"],
        style=row["style"],
        seed=row["seed"],
        file_id=row["file_id"],
        kind=kind or "create",
        source_photos=source_photos,
    )


async def init_db() -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()

        # Idempotent column-add for pre-existing DBs (Railway volume etc).
        cur = await db.execute("PRAGMA table_info(users)")
        existing_cols = {row[1] for row in await cur.fetchall()}
        if "edit_model" not in existing_cols:
            await db.execute(
                f"ALTER TABLE users ADD COLUMN edit_model TEXT DEFAULT '{DEFAULT_EDIT_MODEL}'"
            )
            await db.execute(
                "UPDATE users SET edit_model = ? WHERE edit_model IS NULL",
                (DEFAULT_EDIT_MODEL,),
            )
            logger.info("Added edit_model column (default {})", DEFAULT_EDIT_MODEL)

        # Migration for video, audio, text settings columns
        # Create saved_prompts table if not exists
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        new_columns = {
            "video_model": "TEXT DEFAULT 'ltx-2'",
            "video_aspect_ratio": "TEXT DEFAULT '16:9'",
            "video_duration": "INTEGER DEFAULT 5",
            "audio_model": "TEXT DEFAULT 'openai-audio'",
            "audio_voice": "TEXT DEFAULT 'nova'",
            "text_model": "TEXT DEFAULT 'openai'",
            "image_quality": "TEXT DEFAULT 'medium'",
            "image_transparent": "INTEGER DEFAULT 0"
        }
        for col_name, col_def in new_columns.items():
            if col_name not in existing_cols:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                default_val = col_def.split("DEFAULT ")[1].strip("'")
                if "INTEGER" in col_def:
                    default_val = int(default_val)
                await db.execute(f"UPDATE users SET {col_name} = ? WHERE {col_name} IS NULL", (default_val,))
                logger.info("Added users.{} column (default {})", col_name, default_val)

        cur = await db.execute("PRAGMA table_info(generations)")
        gen_cols = {row[1] for row in await cur.fetchall()}
        if "kind" not in gen_cols:
            await db.execute("ALTER TABLE generations ADD COLUMN kind TEXT DEFAULT 'create'")
            await db.execute("UPDATE generations SET kind = 'create' WHERE kind IS NULL")
            logger.info("Added generations.kind column")
        if "source_photos" not in gen_cols:
            await db.execute("ALTER TABLE generations ADD COLUMN source_photos TEXT")
            logger.info("Added generations.source_photos column")

        # Idempotent migration: rename Pollinations model keys that were
        # deprecated when the API moved to gen.pollinations.ai/v1.
        for old_key, new_key in LEGACY_MODEL_REMAP.items():
            cur = await db.execute(
                "UPDATE users SET model = ? WHERE model = ?",
                (new_key, old_key),
            )
            if cur.rowcount:
                logger.info("Migrated {} user(s): model {} -> {}", cur.rowcount, old_key, new_key)
        await db.commit()
    logger.info("DB initialized at {}", settings.db_path)


@asynccontextmanager
async def _connect():
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def upsert_user(
    telegram_id: int,
    username: str | None,
    language: str,
) -> User:
    async with _connect() as db:
        await db.execute(
            """
            INSERT INTO users (telegram_id, username, language, model, edit_model, aspect_ratio)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username
            """,
            (telegram_id, username, language, DEFAULT_MODEL, DEFAULT_EDIT_MODEL, DEFAULT_RATIO),
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        assert row is not None
        return _row_to_user(row)


async def get_user(telegram_id: int) -> User | None:
    async with _connect() as db:
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        return _row_to_user(row) if row else None


async def get_user_lang(telegram_id: int) -> str | None:
    async with _connect() as db:
        cur = await db.execute(
            "SELECT language FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cur.fetchone()
        return row["language"] if row else None


async def update_user_setting(telegram_id: int, field: str, value: Any) -> None:
    allowed_fields = {
        "model", "edit_model", "aspect_ratio", "style", "language",
        "video_model", "video_aspect_ratio", "video_duration",
        "audio_model", "audio_voice", "text_model",
        "image_quality", "image_transparent"
    }
    if field not in allowed_fields:
        raise ValueError(f"unsupported field: {field}")
    async with _connect() as db:
        await db.execute(
            f"UPDATE users SET {field} = ? WHERE telegram_id = ?",
            (value, telegram_id),
        )
        await db.commit()


async def save_generation(
    user_id: int,
    prompt: str,
    enhanced_prompt: str | None,
    model: str,
    aspect_ratio: str,
    style: str | None,
    seed: int,
    file_id: str | None,
    *,
    kind: str = "create",
    source_photos: list[str] | tuple[str, ...] | None = None,
) -> int:
    sources_json = json.dumps(list(source_photos)) if source_photos else None
    async with _connect() as db:
        cur = await db.execute(
            """
            INSERT INTO generations
                (user_id, prompt, enhanced_prompt, model, aspect_ratio, style,
                 seed, file_id, kind, source_photos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, prompt, enhanced_prompt, model, aspect_ratio, style,
                seed, file_id, kind, sources_json,
            ),
        )
        await db.commit()
        return cur.lastrowid or 0


async def update_generation_file_id(gen_id: int, file_id: str) -> None:
    async with _connect() as db:
        await db.execute(
            "UPDATE generations SET file_id = ? WHERE id = ?",
            (file_id, gen_id),
        )
        await db.commit()


async def get_generation(gen_id: int) -> Generation | None:
    async with _connect() as db:
        cur = await db.execute("SELECT * FROM generations WHERE id = ?", (gen_id,))
        row = await cur.fetchone()
        return _row_to_gen(row) if row else None


async def list_user_generations(user_id: int, limit: int = 10) -> list[Generation]:
    async with _connect() as db:
        cur = await db.execute(
            "SELECT * FROM generations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        return [_row_to_gen(r) for r in rows]


async def add_favorite(user_id: int, generation_id: int) -> bool:
    async with _connect() as db:
        try:
            await db.execute(
                "INSERT INTO favorites (user_id, generation_id) VALUES (?, ?)",
                (user_id, generation_id),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_favorite(user_id: int, generation_id: int) -> None:
    async with _connect() as db:
        await db.execute(
            "DELETE FROM favorites WHERE user_id = ? AND generation_id = ?",
            (user_id, generation_id),
        )
        await db.commit()


async def is_favorite(user_id: int, generation_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND generation_id = ?",
            (user_id, generation_id),
        )
        return await cur.fetchone() is not None


async def list_user_favorites(user_id: int, limit: int = 10) -> list[Generation]:
    async with _connect() as db:
        cur = await db.execute(
            """
            SELECT g.* FROM generations g
            JOIN favorites f ON f.generation_id = g.id
            WHERE f.user_id = ?
            ORDER BY f.created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cur.fetchall()
        return [_row_to_gen(r) for r in rows]


async def save_user_prompt(user_id: int, title: str, prompt_text: str) -> int:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO saved_prompts (user_id, title, prompt_text) VALUES (?, ?, ?)",
            (user_id, title, prompt_text),
        )
        await db.commit()
        return cur.lastrowid


async def list_user_prompts(user_id: int) -> list[dict[str, Any]]:
    async with _connect() as db:
        cur = await db.execute(
            "SELECT id, title, prompt_text, created_at FROM saved_prompts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def delete_user_prompt(user_id: int, prompt_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute(
            "DELETE FROM saved_prompts WHERE user_id = ? AND id = ?",
            (user_id, prompt_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_user_prompt(user_id: int, prompt_id: int) -> dict[str, Any] | None:
    async with _connect() as db:
        cur = await db.execute(
            "SELECT id, title, prompt_text, created_at FROM saved_prompts WHERE user_id = ? AND id = ?",
            (user_id, prompt_id),
        )
        row = await cur.fetchone()
        return dict(row) if row else None
