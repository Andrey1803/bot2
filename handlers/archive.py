from aiogram import Router, types
from aiogram.filters import Command

import db
from .registration import user_menu_keyboard  # ✅ меню пользователя

router = Router()


@router.message(Command("archive"))
async def cmd_archive(message: types.Message):
    await db.archive_old_tasks()
    await db.delete_old_tasks()
    backup_path = await db.backup_database()

    await message.answer(
        "📦 Архивация завершена!\n"
        f"💾 Резервная копия сохранена: <code>{backup_path}</code>",
        reply_markup=user_menu_keyboard()
    )
