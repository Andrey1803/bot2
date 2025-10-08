import asyncio
import aiosqlite
import csv
from db import DB_PATH

async def import_users():
    async with aiosqlite.connect(DB_PATH) as db:
        with open("clients.csv", newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tg_user_id = int(row["tg_user_id"])
                full_name = row["full_name"] or None
                phone = row["phone"] or None
                address = row["address"] or None
                created_at = row["created_at"] or None
                due_at = row["due_at"] or None

                await db.execute("""
                    INSERT OR REPLACE INTO users (tg_user_id, name, phone, address, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (tg_user_id, full_name, phone, address, created_at))

                if due_at:
                    await db.execute("""
                        INSERT INTO reminders (tg_user_id, due_at) VALUES (?, ?)
                    """, (tg_user_id, due_at))

        await db.commit()
        print("✅ Импорт завершён")

asyncio.run(import_users())
