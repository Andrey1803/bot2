import asyncio
import logging
import os
import time
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
load_dotenv()  # ✅ сначала загружаем .env

from config import API_TOKEN, ADMIN_ID, PROXY_URL

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp_socks import ProxyConnector
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiosqlite

from aiogram.fsm.storage.memory import MemoryStorage  # FSM-хранилище

# Импортируем роутеры
from handlers import registration, service_choice, create_task, debug, archive, stats, graph, admin
import db


class LoggingMiddleware:
    async def __call__(self, handler, event, data):
        start = time.time()
        result = await handler(event, data)
        duration = time.time() - start
        logging.info(f"Handled {type(event).__name__} in {duration:.3f}s")
        return result


async def scheduled_archive():
    logging.info("⏳ Запускаю авто‑архивацию...")
    await db.archive_old_tasks()
    await db.delete_old_tasks()
    await db.backup_database()


async def send_reminders(bot: Bot):
    reminders = await db.get_due_reminders()
    for r in reminders:
        user_id = r["tg_user_id"]
        try:
            await bot.send_message(
                user_id,
                "💧 Напоминание: прошло 180 дней с момента регистрации.\n"
                "Рекомендуем заказать обслуживание скважины."
            )
            await db.delete_reminder(r["id"])
        except Exception as e:
            if "Forbidden" in str(e):
                await db.mark_user_inactive(user_id)
                await db.delete_reminder(r["id"])
                await bot.send_message(
                    ADMIN_ID,
                    f"⚠️ Пользователь {user_id} удалил чат или заблокировал бота.\n"
                    f"Удалён из списка, напоминание удалено."
                )
            else:
                logging.error(f"❌ Ошибка при отправке напоминания {user_id}: {e}")



async def migrate_db():
    """Добавляем недостающие колонки, если база создана раньше"""
    async with aiosqlite.connect(db.DB_PATH) as conn:
        # Добавляем address
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN address TEXT")
            logging.info("✅ Колонка 'address' добавлена в таблицу users")
        except Exception:
            pass  # если уже есть — игнорируем

        # Добавляем is_active
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
            logging.info("✅ Колонка 'is_active' добавлена в таблицу users")
        except Exception:
            pass  # если уже есть — игнорируем

        await conn.commit()



async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler("logs/bot.log", maxBytes=500_000, backupCount=3, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    if not API_TOKEN:
        raise ValueError("❌ Не найден API_TOKEN в .env")

    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Инициализация базы и миграция
    await db.init_db()
    await migrate_db()

    # 👉 Настройка прокси из .env
    session = None
    if PROXY_URL:
        connector = ProxyConnector.from_url(PROXY_URL)
        session = AiohttpSession(connector=connector)

    bot = Bot(
        token=API_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        timeout=30
    )

    # ✅ FSM-хранилище для пользователей
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # Подключаем роутеры
    dp.include_router(registration.router)
    dp.include_router(service_choice.router)
    dp.include_router(create_task.router)
    dp.include_router(debug.router)
    dp.include_router(archive.router)
    dp.include_router(stats.router)
    dp.include_router(graph.router)
    dp.include_router(admin.router)

    # Планировщик
    scheduler = AsyncIOScheduler(timezone="Europe/Minsk")
    scheduler.add_job(scheduled_archive, CronTrigger(day_of_week="mon", hour=3))
    scheduler.add_job(send_reminders, "interval", days=1, args=[bot])
    scheduler.start()

    logging.info("✅ Бот запущен и готов к работе")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("⛔ Бот остановлен вручную")
