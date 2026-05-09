from aiogram import Router, types
from aiogram.filters import Command
import aiosqlite
from .registration import user_menu_keyboard  # ✅ меню пользователя

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    async with aiosqlite.connect("data/bot.db") as db:  # ✅ путь совпадает с db.py
        cursor = await db.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = (await cursor.fetchone())[0]

        cursor = await db.execute("""
            SELECT service_type, COUNT(*) 
            FROM tasks 
            GROUP BY service_type
        """)
        rows = await cursor.fetchall()

    text = f"📊 Статистика заявок:\n\nВсего заявок: {total_tasks}\n\n"
    for service_type, count in rows:
        text += f"• {service_type}: {count}\n"

    await message.answer(text, reply_markup=user_menu_keyboard())
