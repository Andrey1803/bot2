import aiosqlite
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join("data", "bot.db")


async def init_db():
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_user_id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            address TEXT,
            created_at TEXT
        )""")
        # Таблица задач (добавлены task_id и task_url)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            task_url TEXT,
            name TEXT,
            service_type TEXT,
            tg_user_id INTEGER,
            created_at TEXT
        )""")
        # Таблица напоминаний
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_user_id INTEGER,
            due_at TEXT
        )""")
        await db.commit()

async def delete_reminder(reminder_id: int):
    """Удаляет напоминание по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await db.commit()


async def get_due_reminders():
    """Возвращает напоминания, срок которых наступил, только для активных пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT r.id, r.tg_user_id
            FROM reminders r
            JOIN users u ON r.tg_user_id = u.tg_user_id
            WHERE r.due_at <= ? AND u.is_active = 1
        """, (datetime.utcnow().isoformat(),))
        rows = await cur.fetchall()
        return [{"id": row["id"], "tg_user_id": row["tg_user_id"]} for row in rows]



async def save_user(tg_user_id: int, name: str, phone: str, address: str):
    """Сохраняем или обновляем пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (tg_user_id, name, phone, address, created_at) VALUES (?, ?, ?, ?, ?)",
            (tg_user_id, name, phone, address, datetime.utcnow().isoformat())
        )
        # Добавим напоминание через 180 дней
        due = (datetime.utcnow() + timedelta(days=180)).isoformat()
        await db.execute("INSERT INTO reminders (tg_user_id, due_at) VALUES (?, ?)", (tg_user_id, due))
        await db.commit()


async def get_user(tg_user_id: int):
    """Получаем пользователя по Telegram ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE tg_user_id = ?", (tg_user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def save_task(tg_user_id: int, name: str, service_type: str, task_id: str = None, task_url: str = None):
    """Сохраняем задачу вместе с ID и ссылкой из Yougile"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tasks (task_id, task_url, name, service_type, tg_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, task_url, name, service_type, tg_user_id, datetime.utcnow().isoformat())
        )
        await db.commit()


async def get_all_users():
    """Возвращаем список всех пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT tg_user_id, name, phone, address, created_at FROM users ORDER BY created_at ASC")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def mark_user_inactive(tg_user_id: int):
    """Помечает пользователя как неактивного (удалил чат или заблокировал бота)"""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET is_active = 0 WHERE tg_user_id = ?",
            (tg_user_id,)
        )
        await conn.commit()


async def get_due_users_within_month():
    """Возвращаем пользователей, у которых обслуживание в ближайший месяц"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.utcnow()
        next_month = now + timedelta(days=30)
        cur = await db.execute(
            """
            SELECT u.tg_user_id, u.name, u.phone, u.address, r.due_at
            FROM users u
            JOIN reminders r ON u.tg_user_id = r.tg_user_id
            WHERE r.due_at BETWEEN ? AND ?
            ORDER BY r.due_at ASC
            """,
            (now.isoformat(), next_month.isoformat())
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
