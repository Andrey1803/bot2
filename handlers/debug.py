from aiogram import Router, types
from aiogram.filters import Command

import db
from .registration import user_menu_keyboard  # ✅ меню пользователя

router = Router()


@router.message(Command("me"))
async def cmd_me(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы ещё не зарегистрированы. Используйте /start.")
        return

    await message.answer(
        f"👤 Ваш профиль:\n\n"
        f"ID: {user['tg_user_id']}\n"
        f"Имя: {user['name']}\n"
        f"Телефон: {user['phone']}\n"
        f"Адрес: {user.get('address', 'не указан')}",
        reply_markup=user_menu_keyboard()
    )


@router.message(Command("mytasks"))
async def cmd_mytasks(message: types.Message):
    tasks = await db.get_tasks_by_user(message.from_user.id)
    if not tasks:
        await message.answer("📭 У вас пока нет заявок.", reply_markup=user_menu_keyboard())
        return

    text = "📋 Ваши заявки:\n\n"
    for t in tasks:
        text += f"• {t[0]} | {t[1]} | {t[2][:10]}\n"

    await message.answer(text, reply_markup=user_menu_keyboard())
