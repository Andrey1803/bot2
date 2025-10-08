from aiogram import Router, types
from aiogram.filters import Command

import db
from .registration import admin_menu_keyboard
from config import ADMIN_ID   # ✅ теперь берём из config.py

router = Router()


# 👥 Количество абонентов
@router.message(Command("users"))
@router.message(lambda m: m.text == "👥 Количество абонентов")
async def list_users(message: types.Message):
    if not ADMIN_ID or message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    users = await db.get_all_users()
    if not users:
        await message.answer(
            "📭 Пока нет зарегистрированных пользователей.",
            reply_markup=admin_menu_keyboard()
        )
        return

    text_lines = [
        f"👥 Всего пользователей: {len(users)}\n"
    ]
    for u in users:
        text_lines.append(
            f"• {u['name']} | 📱 {u['phone']} | 🏠 {u['address']} | ID: {u['tg_user_id']}"
        )

    await message.answer("\n".join(text_lines), reply_markup=admin_menu_keyboard())


# ⏰ Ближайшие обслуживания (30 дней)
@router.message(Command("due"))
@router.message(lambda m: m.text == "⏰ Ближайшие обслуживания (30 дней)")
async def list_due_users(message: types.Message):
    if not ADMIN_ID or message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    due_users = await db.get_due_users_within_month()
    if not due_users:
        await message.answer(
            "✅ В ближайшие 30 дней обслуживаний нет.",
            reply_markup=admin_menu_keyboard()
        )
        return

    text_lines = ["⏰ Пользователи с обслуживанием в ближайшие 30 дней:\n"]
    for u in due_users:
        text_lines.append(
            f"• {u['name']} | 📱 {u['phone']} | 🏠 {u['address']} | до {u['due_at'][:10]}"
        )

    await message.answer("\n".join(text_lines), reply_markup=admin_menu_keyboard())
