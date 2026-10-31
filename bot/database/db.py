
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "silkinyaptimi.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                timezone TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Eski bazada timezone ustuni bo'lmasligi mumkin.
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if "timezone" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN timezone TEXT")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # event_key: manbadagi hodisa ID'si, masalan «USGS:us7000abcd».
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_notifications (
                user_id INTEGER NOT NULL,
                event_key TEXT NOT NULL,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, event_key)
            )
        """)

        # «Silkindimi?» bosilgandan keyin vaqtincha kuzatish.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS watches (
                user_id INTEGER PRIMARY KEY,
                expires_at TEXT NOT NULL,
                found INTEGER DEFAULT 0
            )
        """)

        await db.commit()


async def save_location(user_id, latitude, longitude, timezone_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, latitude, longitude, timezone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                timezone = excluded.timezone,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, latitude, longitude, timezone_name))

        await db.commit()


async def get_location(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT latitude, longitude, timezone
            FROM users
            WHERE user_id = ?
              AND latitude IS NOT NULL
              AND longitude IS NOT NULL
        """, (user_id,)) as cursor:
            return await cursor.fetchone()


async def subscribe_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO subscriptions (user_id, is_active)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET is_active = 1
        """, (user_id,))

        await db.commit()


async def unsubscribe_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE subscriptions
            SET is_active = 0
            WHERE user_id = ?
        """, (user_id,))

        await db.commit()


async def get_users_to_monitor():
    """Obunachilar va hozir kuzatuvdagi foydalanuvchilar."""

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT users.user_id, users.latitude, users.longitude,
                   users.timezone
            FROM users
            WHERE users.latitude IS NOT NULL
              AND users.longitude IS NOT NULL
              AND (
                  users.user_id IN (
                      SELECT user_id FROM subscriptions
                      WHERE is_active = 1
                  )
                  OR users.user_id IN (
                      SELECT user_id FROM watches
                      WHERE expires_at > datetime('now')
                  )
              )
        """) as cursor:
            return await cursor.fetchall()


async def start_watch(user_id, minutes):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO watches (user_id, expires_at, found)
            VALUES (?, datetime('now', ?), 0)
            ON CONFLICT(user_id) DO UPDATE SET
                expires_at = excluded.expires_at,
                found = 0
        """, (user_id, f"+{minutes} minutes"))

        await db.commit()


async def mark_watch_found(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE watches SET found = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def pop_finished_watches():
    """Muddati tugagan kuzatuvlarni o'chiradi.

    Hech narsa topilmagan foydalanuvchilar ro'yxatini qaytaradi.
    """

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id FROM watches
            WHERE expires_at <= datetime('now') AND found = 0
        """) as cursor:
            rows = await cursor.fetchall()

        await db.execute(
            "DELETE FROM watches WHERE expires_at <= datetime('now')"
        )
        await db.commit()

    return [row[0] for row in rows]


async def notification_already_sent(user_id, event_keys):
    """Hodisaning birorta manba ID'si bo'yicha xabar yuborilganmi."""

    placeholders = ", ".join("?" for _ in event_keys)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"""
            SELECT 1 FROM sent_notifications
            WHERE user_id = ? AND event_key IN ({placeholders})
        """, (user_id, *event_keys)) as cursor:
            return await cursor.fetchone() is not None


async def mark_notification_sent(user_id, event_keys):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany("""
            INSERT OR IGNORE INTO sent_notifications (user_id, event_key)
            VALUES (?, ?)
        """, [(user_id, key) for key in event_keys])
        await db.commit()


async def delete_old_notifications(days=3):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM sent_notifications WHERE sent_at < datetime('now', ?)",
            (f"-{days} days",)
        )
        await db.commit()
