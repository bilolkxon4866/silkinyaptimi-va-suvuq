
import json

import aiosqlite

from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "sovuq.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                timezone TEXT NOT NULL,
                elevation REAL,
                alerts_on INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Arxiv xulosasi o'zgarmaydi: bir marta hisoblab saqlaymiz.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS climate_cache (
                grid_key TEXT NOT NULL,
                period TEXT NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY (grid_key, period)
            )
        """)

        # Har bir tun uchun yuborilgan eng yuqori daraja va kechki eslatma.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                user_id INTEGER NOT NULL,
                morning TEXT NOT NULL,
                level INTEGER NOT NULL,
                evening_sent INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, morning)
            )
        """)

        await db.commit()


async def save_user(user_id, latitude, longitude, timezone_name, elevation):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users
                (user_id, latitude, longitude, timezone, elevation)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                timezone = excluded.timezone,
                elevation = excluded.elevation,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, latitude, longitude, timezone_name, elevation))

        # Joy o'zgarsa, eski tunlar haqidagi belgilar ma'nosiz.
        await db.execute("DELETE FROM alerts WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()


async def get_alert_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            "SELECT * FROM users WHERE alerts_on = 1"
        ) as cursor:
            return await cursor.fetchall()


async def set_alerts(user_id, enabled):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET alerts_on = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id)
        )
        await db.commit()


def _encode_dates(value):
    if isinstance(value, date):
        return {"__date__": value.isoformat()}

    raise TypeError(value)


def _decode_dates(value):
    if "__date__" in value:
        return date.fromisoformat(value["__date__"])

    return value


async def get_climate(grid_key, period):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT data FROM climate_cache
            WHERE grid_key = ? AND period = ?
        """, (grid_key, period)) as cursor:
            row = await cursor.fetchone()

    if row is None:
        return None

    return json.loads(row[0], object_hook=_decode_dates)


async def save_climate(grid_key, period, climate):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO climate_cache (grid_key, period, data)
            VALUES (?, ?, ?)
        """, (grid_key, period, json.dumps(climate, default=_encode_dates)))
        await db.commit()


async def get_alert(user_id, morning):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT level, evening_sent FROM alerts
            WHERE user_id = ? AND morning = ?
        """, (user_id, morning.isoformat())) as cursor:
            return await cursor.fetchone()


async def save_alert(user_id, morning, level, evening_sent):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO alerts (user_id, morning, level, evening_sent)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, morning) DO UPDATE SET
                level = MAX(level, excluded.level),
                evening_sent = MAX(evening_sent, excluded.evening_sent)
        """, (user_id, morning.isoformat(), level, int(evening_sent)))
        await db.commit()


async def delete_old_alerts():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM alerts WHERE morning < date('now', '-3 days')"
        )
        await db.commit()
