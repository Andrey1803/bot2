import asyncio
import logging
import re
import json
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from collections import Counter

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile,
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import API_TOKEN, ADMIN_ID, YOUGILE_WEBHOOK_SECRET
from tools.yougile_api import create_task, search_tasks_by_user, get_tasks_for_stats, get_column_name

import aiofiles

from fastapi import FastAPI, Request, HTTPException
import uvicorn

# ─── Настройка логирования ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Рабочее время (для автоответчика) ───────────────────────────────────────
# Часовой пояс: Europe/Minsk (UTC+3)
WORK_TZ_HOURS = 3  # UTC+3 для Беларуси
WORK_START_HOUR = 8  # 08:00
WORK_END_HOUR = 20   # 20:00

# ─── Пути к данным ───────────────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
USER_FILE = "data/users.json"
ORDER_LOG = "data/orders.log"

# ─── Инициализация файлов данных ─────────────────────────────────────────────
# ─── Резервная копия пользователей (для инициализации пустого Volume) ────────
DEFAULT_USERS = {
    "5567898807": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "вцьоащц", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375291472109", "last_order_id": None, "last_address": None, "ratings": []},
    "5185948718": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Ната", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375447408978", "last_order_id": None, "last_address": None, "ratings": []},
    "7599242480": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Козырева Майя", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375295034840", "last_order_id": None, "last_address": "Колодищи 2, ул. Рябиновая, д. 10", "ratings": []},
    "6445132705": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Татьяна", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375293608308", "last_order_id": None, "last_address": "Минская область, Дзержинский район, д. Каменка, ул. Центральная д. 7", "ratings": []},
    "449621760": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Гаврош", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375447779866", "last_order_id": None, "last_address": "Логойский р-н, Беларучский с/с, СТ Текстиль, уч. 23", "ratings": []},
    "586923354": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Виктор", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375296160955", "last_order_id": None, "last_address": "Логойский район ст малиновка 2001, солнечная 192", "ratings": []},
    "750303531": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Игорь", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375296317433", "last_order_id": None, "last_address": "СТ НИВА Ф 188", "ratings": []},
    "508334961": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Сергей", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375296772018", "last_order_id": None, "last_address": "Заславль ул Строительная2", "ratings": []},
    "650648039": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Ирина", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375293697683", "last_order_id": None, "last_address": "Раубичи земляничная 3", "ratings": []},
    "1243322312": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Вячеслав Глеб", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375296562038", "last_order_id": None, "last_address": "Марьяливо, улица Центральная 43А", "ratings": []},
    "486713249": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Павел", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375296465638", "last_order_id": None, "last_address": "Аг.Острошицы, ул. Парижской Коммуны,5А", "ratings": []},
    "460143593": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Александр", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375296499005", "last_order_id": None, "last_address": "Д.Чуденичи, Широкая 10", "ratings": []},
    "432775666": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Татьяна", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375296450385", "last_order_id": None, "last_address": "Колодищи, ул.Беловежская,7а", "ratings": []},
    "515325398": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Василий", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375296344480", "last_order_id": None, "last_address": "д. Дроздово, ул. Полевая, 19", "ratings": []},
    "814067080": {"joined": "2026-04-11T19:30:00", "username": None, "full_name": "Анна", "reminder_sent": False, "last_reminder_sent": None, "phone": "+375293101429", "last_order_id": None, "last_address": None, "ratings": []},
}

def _init_data_files():
    """Инициализирует файлы данных."""
    os.makedirs("data", exist_ok=True)
    
    print(f"🐍 PWD: {os.getcwd()}")
    print(f"📂 Files in data/: {os.listdir('data')}")
    sys.stdout.flush()

    needs_restore = False
    if not os.path.exists(USER_FILE):
        print("⚠️ users.json не существует — восстановим")
        needs_restore = True
    else:
        size = os.path.getsize(USER_FILE)
        print(f"📊 users.json размер: {size} байт")
        if size == 0:
            print("⚠️ users.json пустой (0 байт) — восстановим")
            needs_restore = True
        else:
            try:
                with open(USER_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                print(f"📄 users.json содержимое: {content[:100]}...")
                if not content or content == "{}" or content == "[]":
                    print("⚠️ users.json пустой — восстановим")
                    needs_restore = True
                else:
                    data = json.loads(content)
                    print(f"👥 Текущих пользователей: {len(data)}")
                    if len(data) < 2:
                        print("⚠️ Мало пользователей — восстановим")
                        needs_restore = True
            except Exception as e:
                print(f"⚠️ Ошибка чтения users.json: {e} — восстановим")
                needs_restore = True

    if needs_restore:
        print("🔨 ЗАПИСЬ USERS.JSON...")
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_USERS, f, ensure_ascii=False, indent=2)
        print(f"✅ users.json восстановлен: {len(DEFAULT_USERS)} пользователей")
    else:
        print("✅ users.json в порядке")
    
    sys.stdout.flush()

# Вызываем до настройки логирования, используем print
_init_data_files()

# ─── Бот и диспетчер ─────────────────────────────────────────────────────────
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# ─── FSM состояния ───────────────────────────────────────────────────────────
class OrderForm(StatesGroup):
    category = State()       # Выбор категории услуги
    name = State()
    phone = State()
    address = State()
    comment = State()
    photo = State()          # Фото к заказу


class BroadcastForm(StatesGroup):
    message = State()


class RatingForm(StatesGroup):
    rating = State()


# ─── Категории услуг ────────────────────────────────────────────────────────
SERVICE_CATEGORIES = {
    "🔧 Ремонт": "Ремонт оборудования",
    "🏗️ Монтаж": "Монтажные работы",
    "🧹 Обслуживание": "Техническое обслуживание",
    "📋 Консультация": "Консультация специалиста",
}

# ─── Периодичность ТО (в месяцах) ──────────────────────────────────────────
MAINTENANCE_INTERVAL_MONTHS = 6


def category_kb():
    """Клавиатура с категориями услуг."""
    buttons = [[KeyboardButton(text=cat)] for cat in SERVICE_CATEGORIES.keys()]
    buttons.append([KeyboardButton(text="❌ Отмена")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def skip_inline_kb():
    """Inline-кнопка 'Пропустить'."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_field")]
    ])


def main_menu_kb(user_data: dict = None):
    """Главное меню. Если админ — показываем админ-панель."""
    buttons = [[KeyboardButton(text="🧾 Сделать заказ")]]

    # Если у пользователя есть сохранённый телефон — предлагаем повтор
    if user_data and user_data.get("phone"):
        buttons.append([KeyboardButton(text="🔄 Повторить заказ")])

    buttons.append([KeyboardButton(text="📋 Мои заказы")])
    buttons.append([KeyboardButton(text="👤 Мой профиль")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def main_menu_kb_with_admin(user_id: str, user_data: dict = None):
    """Главное меню с проверкой админа по user_id."""
    buttons = [[KeyboardButton(text="🧾 Сделать заказ")]]

    if user_data and user_data.get("phone"):
        buttons.append([KeyboardButton(text="🔄 Повторить заказ")])

    buttons.append([KeyboardButton(text="📋 Мои заказы")])
    buttons.append([KeyboardButton(text="👤 Мой профиль")])

    # Админ-кнопка — проверка по реальному ID
    is_admin = (str(user_id) == str(ADMIN_ID))
    logger.info(f"🔍 Проверка админа: user_id={user_id}, ADMIN_ID={ADMIN_ID}, is_admin={is_admin}")
    if is_admin:
        buttons.append([KeyboardButton(text="🛡️ Админ-панель")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def admin_panel_kb():
    """Клавиатура админ-панели."""
    buttons = [
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🔧 ТО статус"), KeyboardButton(text="📢 Рассылка")],
        [KeyboardButton(text="📥 Экспорт CSV")],
        [KeyboardButton(text="🔙 Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def rating_kb():
    """Клавиатура для оценки качества."""
    buttons = [
        [
            InlineKeyboardButton(text="⭐ 1", callback_data="rate:1"),
            InlineKeyboardButton(text="⭐ 2", callback_data="rate:2"),
            InlineKeyboardButton(text="⭐ 3", callback_data="rate:3"),
        ],
        [
            InlineKeyboardButton(text="⭐ 4", callback_data="rate:4"),
            InlineKeyboardButton(text="⭐ 5", callback_data="rate:5"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Утилиты ─────────────────────────────────────────────────────────────────
def phone_is_valid(phone: str) -> bool:
    """Проверяет, что телефон содержит 10-14 цифр (поддержка BY номеров)."""
    digits = re.sub(r"\D", "", phone)
    return 10 <= len(digits) <= 15


def normalize_phone(phone: str) -> str:
    """Нормализует телефон. Для BY: +375XXXXXXXXX."""
    digits = re.sub(r"\D", "", phone)
    # Если начинается с 8 и 12 цифр (Беларусь) → +375
    if len(digits) == 12 and digits[0] == "8":
        digits = "375" + digits[1:]
    # Если 9 цифр (Беларусь без кода) → +375
    if len(digits) == 9:
        digits = "375" + digits
    # Если начинается с 8 и 11 цифр (Россия) → +7
    if len(digits) == 11 and digits[0] == "8":
        digits = "7" + digits[1:]
    # Если 10 цифр (Россия без кода) → +7
    if len(digits) == 10:
        digits = "7" + digits
    return "+" + digits


def is_work_time() -> bool:
    """Проверяет, находится ли текущее время в рабочем диапазоне."""
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.replace(tzinfo=timezone.utc)  # UTC
    # Для простоты используем UTC; если нужно — добавьте смещение
    hour = now_local.hour
    return WORK_START_HOUR <= hour < WORK_END_HOUR


def get_last_order(user_id: str) -> dict | None:
    """Извлекает последний заказ пользователя из лога."""
    try:
        with open(ORDER_LOG, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    # Ищем заказы по ID пользователя
    pattern = rf"🆔 Клиент:.*\(id: <code>{user_id}</code>\)"
    matches = list(re.finditer(pattern, content))
    if not matches:
        return None

    # Берём последнее совпадение + контекст до него
    last_match = matches[-1]
    # Ищем начало этого заказа (📦 <b>Новый заказ</b>)
    start = content.rfind("📦", 0, last_match.start())
    if start == -1:
        start = last_match.start() - 200

    order_text = content[start:last_match.end()].strip()
    return {"text": order_text}


# ─── Асинхронная работа с пользователями ─────────────────────────────────────
_users_lock = asyncio.Lock()
_users_cache: dict = {}


async def load_users() -> dict:
    """Асинхронная загрузка пользователей с кэшированием."""
    global _users_cache
    if _users_cache:
        return _users_cache

    try:
        async with aiofiles.open(USER_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            _users_cache = json.loads(content)
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при загрузке users.json: {e}")
        _users_cache = {}

    return _users_cache


async def save_users(users: dict):
    """Асинхронное сохранение пользователей с блокировкой."""
    global _users_cache
    async with _users_lock:
        _users_cache = users
        tmp_file = USER_FILE + ".tmp"
        try:
            async with aiofiles.open(tmp_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(users, ensure_ascii=False, indent=2))
            if os.path.exists(USER_FILE):
                os.replace(tmp_file, USER_FILE)
            else:
                os.rename(tmp_file, USER_FILE)
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении users.json: {e}")
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            raise


async def update_user_field(user_id: str, field: str, value):
    """Обновляет одно поле пользователя."""
    users = await load_users()
    if user_id in users:
        users[user_id][field] = value
        await save_users(users)


# ─── Миграция старого формата ────────────────────────────────────────────────
async def migrate_old_format():
    """Миграция users.json из старого формата."""
    users = await load_users()
    migrated = False
    for uid, data in list(users.items()):
        if isinstance(data, str):
            users[uid] = {
                "joined": data,
                "username": None,
                "full_name": None,
                "reminder_sent": False,
                "last_reminder_sent": None,
                "phone": None,
                "last_order_id": None,
                "ratings": [],
            }
            migrated = True
        elif isinstance(data, dict):
            for key, default in [
                ("reminder_sent", False),
                ("last_reminder_sent", None),
                ("phone", None),
                ("last_order_id", None),
                ("last_address", None),
                ("ratings", []),
            ]:
                if key not in data:
                    data[key] = default
                    migrated = True
            if "joined" not in data:
                data["joined"] = datetime.now().isoformat()
                migrated = True

    if migrated:
        await save_users(users)
        logger.info("✅ Миграция users.json завершена")


# ─── Проверка при запуске ────────────────────────────────────────────────────
def check_startup():
    """Проверяет обязательные параметры."""
    if ADMIN_ID is None:
        logger.warning("⚠️ ADMIN_ID не задан! Бот не сможет уведомлять администратора.")
    else:
        logger.info(f"✅ ADMIN_ID: {ADMIN_ID}")


# ─── Фича 6: Автоответчик вне рабочего времени ──────────────────────────────
async def check_work_hours(message: types.Message) -> bool:
    """Если вне рабочего времени — предупреждает и возвращает True."""
    if not is_work_time():
        await message.answer(
            "🌙 Спасибо за обращение! Сейчас мы не работаем.\n"
            f"🕐 Наши часы работы: {WORK_START_HOUR}:00 — {WORK_END_HOUR}:00\n"
            "Ваш заказ будет обработан в ближайшее рабочее время."
        )
        return True
    return False


# ═════════════════════════════════════════════════════════════════════════════
# ─── Обработчики команд ─────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@dp.message(Command("restore"))
async def cmd_restore(message: types.Message):
    """Ручное восстановление базы пользователей."""
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return

    global _users_cache
    _users_cache = DEFAULT_USERS.copy()

    try:
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_USERS, f, ensure_ascii=False, indent=2)
        await message.answer(f"✅ База восстановлена! {len(DEFAULT_USERS)} пользователей.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    logger.info(f"👤 /start от user_id={user_id}, full_name={message.from_user.full_name}")
    # Очищаем FSM — чтобы админ не оставался в состоянии заказа
    await state.clear()
    users = await load_users()

    # Если пользователь уже был — не перезаписываем телефон
    if user_id in users:
        users[user_id]["joined"] = datetime.now().isoformat()
        users[user_id]["username"] = message.from_user.username
        if users[user_id].get("full_name") is None:
            users[user_id]["full_name"] = message.from_user.full_name
    else:
        users[user_id] = {
            "joined": datetime.now().isoformat(),
            "username": message.from_user.username,
            "full_name": message.from_user.full_name,
            "reminder_sent": False,
            "last_reminder_sent": None,
            "phone": None,
            "last_order_id": None,
            "ratings": [],
        }
    await save_users(users)

    user_data = users[user_id]
    next_maint = calc_next_maintenance(user_data.get("joined"))
    maint_info = ""
    if next_maint:
        maint_info = f"\n📅 Следующее ТО: {next_maint.strftime('%d.%m.%Y')}"

    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я приму ваш заказ и передам менеджеру.\n"
        "Нажмите кнопку ниже, чтобы оформить заявку."
        f"{maint_info}",
        reply_markup=main_menu_kb_with_admin(str(message.from_user.id), user_data)
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    users = await load_users()
    user_data = users.get(str(message.from_user.id), {})

    # Информация о следующем ТО
    next_maint = calc_next_maintenance(user_data.get("joined"))
    maint_info = ""
    if next_maint:
        days = (next_maint - datetime.now()).days
        if days <= 0:
            maint_info = f"\n\n🔧 <b>ТО просрочено!</b> Рекомендуется записаться на обслуживание."
        else:
            maint_info = f"\n\n📅 <b>Следующее ТО:</b> {next_maint.strftime('%d.%m.%Y')} (через {days} дн.)"

    await message.answer(
        "📋 <b>Доступные команды:</b>\n\n"
        "/start — Начать работу с ботом\n"
        "/help — Показать это сообщение\n"
        "/profile — Мой профиль и дата ТО\n"
        "/status — Статус последнего заказа\n"
        "/rate — Оценить качество обслуживания\n\n"
        "🧾 <b>Кнопки:</b>\n"
        "• Сделать заказ — оформить заявку\n"
        "• Повторить заказ — быстро заказать то же самое\n"
        "• Мои заказы — история заказов\n\n"
        "🕐 Часы работы: 08:00 — 20:00\n"
        f"{maint_info}",
        reply_markup=main_menu_kb_with_admin(str(message.from_user.id), user_data)
    )


@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Показывает профиль пользователя с датой следующего ТО."""
    users = await load_users()
    user_id = str(message.from_user.id)
    user_data = users.get(user_id, {})

    if not user_data:
        await message.answer("⚠️ Вы ещё не зарегистрированы. Нажмите /start")
        return

    name = user_data.get("full_name", "—")
    phone = user_data.get("phone", "—")
    joined = user_data.get("joined", "—")[:10]
    ratings = user_data.get("ratings", [])
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else "нет оценок"

    next_maint = calc_next_maintenance(user_data.get("joined"))
    if next_maint:
        days = (next_maint - datetime.now()).days
        if days <= 0:
            maint_status = f"🔴 Просрочено на {abs(days)} дн."
        else:
            maint_status = f"🟢 Через {days} дн. ({next_maint.strftime('%d.%m.%Y')})"
    else:
        maint_status = "⚪ Не определено"

    text = (
        f"👤 <b>Мой профиль</b>\n\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Дата регистрации: {joined}\n"
        f"Средняя оценка: {avg_rating}\n\n"
        f"🔧 <b>ТО скважины</b> (каждые {MAINTENANCE_INTERVAL_MONTHS} мес.):\n"
        f"Статус: {maint_status}"
    )

    await message.answer(text, reply_markup=main_menu_kb_with_admin(str(message.from_user.id), user_data))


# ─── Фича 2: Статус заказа ──────────────────────────────────────────────────
@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    user_id = str(message.from_user.id)

    # Ищем последние задачи пользователя в YouGile
    try:
        tasks = search_tasks_by_user(user_id, limit=5)
    except Exception as e:
        logger.error(f"Ошибка при поиске задач: {e}")
        # Фоллбэк — поиск в локальном логе
        last_order = get_last_order(user_id)
        if last_order:
            await message.answer(
                "📋 <b>Ваш последний заказ:</b>\n\n"
                f"{last_order['text']}\n\n"
                "ℹ️ Для точного статуса обратитесь к менеджеру."
            )
        else:
            await message.answer("📭 У вас пока нет заказов.")
        return

    if not tasks:
        last_order = get_last_order(user_id)
        if last_order:
            await message.answer(
                "📋 <b>Ваш последний заказ:</b>\n\n"
                f"{last_order['text']}\n\n"
                "ℹ️ Статус задачи в YouGile не удалось получить. Обратитесь к менеджеру."
            )
        else:
            await message.answer("📭 У вас пока нет заказов.")
        return

    # Показываем последние 3 задачи
    for task in tasks[:3]:
        task_id = task.get("id", "—")
        title = task.get("title", "Без названия")
        column_id = task.get("columnId", "")
        column_name = "Загружается..."
        if column_id:
            try:
                column_name = get_column_name(column_id)
            except Exception:
                column_name = column_id

        status_emoji = {
            "Новая": "🆕",
            "В работе": "⏳",
            "Выполнена": "✅",
            "Отменена": "❌",
        }
        emoji = status_emoji.get(column_name, "📋")

        created = task.get("created", "")
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                created_str = created_dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                created_str = created
        else:
            created_str = "—"

        await message.answer(
            f"{emoji} <b>{title}</b>\n"
            f"📋 ID: <code>{task_id}</code>\n"
            f"📌 Статус: {column_name}\n"
            f"📅 Создан: {created_str}"
        )


# ─── Фича 5: Статистика (только админ) ─────────────────────────────────────
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ может просматривать статистику.")
        return

    # Загружаем пользователей
    users = await load_users()
    total_users = len(users)

    # Считаем заказы из лога
    try:
        async with aiofiles.open(ORDER_LOG, "r", encoding="utf-8") as f:
            log_content = await f.read()
    except Exception:
        log_content = ""

    total_orders = log_content.count("📦 <b>Новый заказ</b>")

    # Статистика по категориям из YouGile
    try:
        tasks = get_tasks_for_stats()
        # Группируем по колонкам
        columns = Counter()
        for task in tasks:
            col = task.get("columnId", "unknown")
            columns[col] += 1
    except Exception as e:
        logger.error(f"Ошибка при получении статистики YouGile: {e}")
        columns = {}

    now = datetime.now()
    text = (
        f"📊 <b>Статистика бота</b>\n"
        f"📅 {now.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"📦 Заказов (лог): <b>{total_orders}</b>\n\n"
    )

    if columns:
        text += "📌 Задачи по колонкам (YouGile):\n"
        for col_id, count in columns.most_common(10):
            try:
                col_name = get_column_name(col_id)
            except Exception:
                col_name = col_id[:8] + "..."
            text += f"  • {col_name}: {count}\n"

    # Средний рейтинг
    ratings = []
    for u in users.values():
        if isinstance(u, dict) and u.get("ratings"):
            ratings.extend(u["ratings"])
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        text += f"\n⭐ Средний рейтинг: {avg_rating:.1f}/5 ({len(ratings)} оценок)"

    await message.answer(text)


# ─── Фича 3: Рассылка (только админ) ────────────────────────────────────────
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ может делать рассылки.")
        return

    await message.answer(
        "📢 <b>Режим рассылки</b>\n"
        "Отправьте сообщение, которое нужно разослать всем пользователям.\n"
        "Для отмены введите /cancel"
    )
    await state.set_state(BroadcastForm.message)


@dp.message(BroadcastForm.message)
async def process_broadcast(message: types.Message, state: FSMContext):
    users = await load_users()
    total = len(users)
    sent = 0
    failed = 0

    status_msg = await message.answer(f"📢 Рассылка... 0/{total}")

    for user_id, user_data in users.items():
        try:
            # Копируем сообщение (поддерживает текст, фото, и т.д.)
            if message.text:
                await bot.send_message(int(user_id), message.text)
            sent += 1
        except Exception as e:
            logger.warning(f"Не удалось отправить пользователю {user_id}: {e}")
            failed += 1

        # Обновляем статус каждые 10 сообщений
        if (sent + failed) % 10 == 0:
            try:
                await status_msg.edit_text(f"📢 Рассылка... {sent + failed}/{total}")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего: {total}"
    )
    await state.clear()


# ─── Админ: Отчёт о ТО ──────────────────────────────────────────────────────
@dp.message(Command("maintenance"))
async def cmd_maintenance(message: types.Message):
    """Показывает админу статус ТО всех пользователей."""
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return

    users = await load_users()
    now = datetime.now()
    overdue = []
    soon = []
    ok = []

    for user_id, user_data in sorted(users.items(), key=lambda x: x[1].get("joined", "")):
        if not isinstance(user_data, dict):
            continue
        name = user_data.get("full_name", "—")
        phone = user_data.get("phone", "—")
        joined_str = user_data.get("joined")
        next_maint = calc_next_maintenance(joined_str)

        if not next_maint:
            continue

        days_until = (next_maint - now).days
        reminder_sent = user_data.get("reminder_sent", False)

        if days_until <= 0:
            overdue.append(f"  🔴 {name} | {phone} | ТО просрочено ({abs(days_until)} дн.) | Напоминание: {'✅' if reminder_sent else '❌'}")
        elif days_until <= 30:
            soon.append(f"  🟡 {name} | {phone} | через {days_until} дн. ({next_maint.strftime('%d.%m.%Y')}) | Напоминание: {'✅' if reminder_sent else '❌'}")
        else:
            ok.append(f"  🟢 {name} | через {days_until} дн. ({next_maint.strftime('%d.%m.%Y')})")

    text = f"🔧 <b>Статус ТО</b> (интервал: {MAINTENANCE_INTERVAL_MONTHS} мес.):\n\n"

    if overdue:
        text += f"<b>⚠️ Просрочено ({len(overdue)})</b>:\n" + "\n".join(overdue) + "\n\n"
    if soon:
        text += f"<b>📅 Скоро ({len(soon)})</b>:\n" + "\n".join(soon[:10]) + "\n\n"
    if ok:
        text += f"<b>✅ В норме ({len(ok)})</b>:\n" + "\n".join(ok[:10])

    if len(ok) > 10:
        text += f"\n  ... и ещё {len(ok) - 10}"

    await message.answer(text)


# ─── Админ: Сброс напоминаний ───────────────────────────────────────────────
@dp.message(Command("reset_reminders"))
async def cmd_reset_reminders(message: types.Message):
    """Сбрасывает флаги reminder_sent у всех пользователей."""
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return

    users = await load_users()
    count = 0
    for user_id, user_data in users.items():
        if isinstance(user_data, dict) and user_data.get("reminder_sent"):
            users[user_id]["reminder_sent"] = False
            count += 1

    await save_users(users)
    await message.answer(f"✅ Сброшены напоминания у {count} пользователей.")


# ─── Админ: Заполнить адреса ────────────────────────────────────────────────
@dp.message(Command("fill_addresses"))
async def cmd_fill_addresses(message: types.Message):
    """Заполняет адреса пользователей из DEFAULT_USERS."""
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return

    users = await load_users()
    updated = 0
    for uid, default_data in DEFAULT_USERS.items():
        if uid in users and isinstance(users[uid], dict):
            addr = default_data.get("last_address")
            if addr and not users[uid].get("last_address"):
                users[uid]["last_address"] = addr
                updated += 1

    await save_users(users)
    await message.answer(f"✅ Заполнены адреса у {updated} пользователей.")


# ─── Админ: Экспорт пользователей ───────────────────────────────────────────
@dp.message(Command("export"))
async def cmd_export(message: types.Message):
    """Экспорт всех пользователей в CSV-файл."""
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return

    users = await load_users()
    csv_lines = ["ID,Имя,Телефон,Дата регистрации,Напоминание,Ср. рейтинг"]

    for user_id, user_data in users.items():
        if not isinstance(user_data, dict):
            continue
        name = user_data.get("full_name", "").replace(",", ";")
        phone = user_data.get("phone", "—")
        joined = user_data.get("joined", "—")[:10]
        reminder = "✅" if user_data.get("reminder_sent") else "❌"
        ratings = user_data.get("ratings", [])
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else "—"
        csv_lines.append(f"{user_id},{name},{phone},{joined},{reminder},{avg_rating}")

    csv_content = "\n".join(csv_lines)
    file_path = "data/users_export.csv"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(csv_content)

    await message.answer_document(FSInputFile(file_path), caption=f"📊 Экспорт {len(users)} пользователей")


# ─── Фича 7: Оценка качества ───────────────────────────────────────────────
@dp.message(Command("rate"))
async def cmd_rate(message: types.Message):
    await message.answer(
        "⭐ Оцените качество обслуживания:\n"
        "Нажмите на кнопку ниже или введите число от 1 до 5.",
        reply_markup=rating_kb()
    )


@dp.callback_query(F.data.startswith("rate:"))
async def process_rating(callback: types.CallbackQuery):
    rating = int(callback.data.split(":")[1])
    user_id = str(callback.from_user.id)

    await update_user_field(user_id, "ratings", lambda x: x)  # placeholder
    users = await load_users()
    if user_id in users:
        if "ratings" not in users[user_id]:
            users[user_id]["ratings"] = []
        users[user_id]["ratings"].append(rating)
        await save_users(users)

    emojis = {1: "😞", 2: "😕", 3: "😐", 4: "😊", 5: "🤩"}
    await callback.message.edit_text(
        f"{emojis.get(rating, '⭐')} Спасибо за оценку: {rating}/5!"
    )
    await callback.answer("Оценка сохранена!")


# ═════════════════════════════════════════════════════════════════════════════
# ─── Обработчики заказов ────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

# ─── Фича 9: Повторный заказ ────────────────────────────────────────────────
@dp.message(F.text == "🔄 Повторить заказ")
async def repeat_order(message: types.Message):
    user_id = str(message.from_user.id)
    users = await load_users()
    user_data = users.get(user_id, {})

    if not user_data.get("phone"):
        await message.answer(
            "⚠️ У вас нет сохранённых данных для повторного заказа.\n"
            "Оформите заказ обычным способом — и в следующий раз сможете повторить."
        )
        return

    last_order = get_last_order(user_id)
    if not last_order:
        await message.answer("⚠️ Не удалось найти ваш последний заказ.")
        return

    # Подтверждение
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🔄 <b>Повторить последний заказ?</b>\n\n"
        f"{last_order['text']}\n\n"
        "Нажмите «✅ Подтвердить» или «❌ Отмена».",
        reply_markup=kb
    )
    # Сохраняем в FSM для следующего шага
    state_data = await dp.storage.get_data(chat_id=message.chat.id, user_id=message.from_user.id)
    state_data["repeat_order"] = True
    await dp.storage.set_data(chat_id=message.chat.id, user_id=message.from_user.id, data=state_data)


@dp.message(F.text == "✅ Подтвердить")
async def confirm_repeat_order(message: types.Message):
    user_id = str(message.from_user.id)
    users = await load_users()
    user_data = users.get(user_id, {})

    name = user_data.get("full_name", message.from_user.full_name)
    phone = user_data.get("phone", "—")

    # Ищем адрес и комментарий в последнем заказе
    last_order = get_last_order(user_id)
    address = "—"
    comment = "Повторный заказ"
    if last_order:
        addr_match = re.search(r"📍 Адрес: (.+)", last_order["text"])
        comm_match = re.search(r"💬 Комментарий: (.+)", last_order["text"])
        if addr_match:
            address = addr_match.group(1)
        if comm_match and comm_match.group(1) != "—":
            comment = comm_match.group(1) + " (повтор)"

    summary = (
        "🔄 <b>Повторный заказ</b>\n"
        f"👤 Имя: {name}\n"
        f"📱 Телефон: {phone}\n"
        f"📍 Адрес: {address}\n"
        f"💬 Комментарий: {comment}\n"
        f"🆔 Клиент: {message.from_user.full_name} (id: <code>{message.from_user.id}</code>)"
    )

    # Уведомляем админа
    if ADMIN_ID is not None:
        try:
            await bot.send_message(ADMIN_ID, summary)
        except Exception as e:
            logger.error(f"❌ Не удалось уведомить админа: {e}")

    async with aiofiles.open(ORDER_LOG, "a", encoding="utf-8") as f:
        await f.write(summary + "\n\n")

    try:
        task = create_task(title=f"Повторный заказ от {name}", description=summary)
        await message.answer(
            f"✅ Повторный заказ принят!\n"
            f"📋 ID задачи: <code>{task.get('id', '—')}</code>",
            reply_markup=main_menu_kb_with_admin(str(message.from_user.id), user_data)
        )
    except Exception as e:
        logger.exception("❌ Ошибка при создании задачи в YouGile")
        await message.answer(
            f"⚠️ Заказ принят, но ошибка в YouGile: {e}",
            reply_markup=main_menu_kb_with_admin(str(message.from_user.id), user_data)
        )

    # Очищаем FSM
    await dp.storage.clear(chat_id=message.chat.id, user_id=message.from_user.id)


# ─── Фича 8: Категории услуг + обычный заказ ───────────────────────────────
@dp.message(F.text == "🧾 Сделать заказ")
async def start_order(message: types.Message, state: FSMContext):
    # Проверяем рабочее время
    await check_work_hours(message)

    await state.set_state(OrderForm.category)
    await message.answer(
        "Выберите тип услуги:",
        reply_markup=category_kb()
    )


@dp.message(OrderForm.category)
async def process_category(message: types.Message, state: FSMContext):
    if message.text not in SERVICE_CATEGORIES:
        await message.answer("Пожалуйста, выберите категорию из списка:")
        return

    await state.update_data(category=message.text)
    await state.set_state(OrderForm.name)

    users = await load_users()
    user_id = str(message.from_user.id)
    user_data = users.get(user_id, {})

    # Если есть сохранённое имя — предлагаем его
    saved_name = user_data.get("full_name")
    if saved_name:
        await message.answer(
            f"Ваше имя: <b>{saved_name}</b>?\n"
            "Введите новое или отправьте «Да»:",
            reply_markup=cancel_kb()
        )
    else:
        await message.answer("Введите ваше имя:", reply_markup=cancel_kb())


@dp.message(OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введите ваше имя:")
        return
    if name.lower() in ("да", "yes", "ok"):
        users = await load_users()
        user_id = str(message.from_user.id)
        name = users.get(user_id, {}).get("full_name", name)

    await state.update_data(name=name)
    await state.set_state(OrderForm.phone)

    # Фича 1: Если телефон уже сохранён — предлагаем его
    users = await load_users()
    user_id = str(message.from_user.id)
    user_data = users.get(user_id, {})
    saved_phone = user_data.get("phone")

    if saved_phone:
        await message.answer(
            f"Ваш телефон: <b>{saved_phone}</b>?\n"
            "Введите новый или отправьте «Да»:",
            reply_markup=cancel_kb()
        )
    else:
        await message.answer(
            "Введите ваш телефон:\n"
            "<i>(формат: +375XXXXXXXXX или 8XXXXXXXXXX)</i>",
            reply_markup=cancel_kb()
        )


@dp.message(OrderForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()

    # Если "Да" — используем сохранённый
    if phone.lower() in ("да", "yes", "ok"):
        users = await load_users()
        user_id = str(message.from_user.id)
        phone = users.get(user_id, {}).get("phone", "")
        if not phone:
            await message.answer("У вас нет сохранённого телефона. Введите номер:")
            return
        await state.update_data(phone=phone)
        await state.set_state(OrderForm.address)
        await message.answer("Введите адрес объекта:", reply_markup=cancel_kb())
        return

    if not phone_is_valid(phone):
        await message.answer(
            "Некорректный номер. Введите телефон ещё раз:\n"
            "<i>(нужно 10-15 цифр)</i>"
        )
        return

    normalized = normalize_phone(phone)
    await state.update_data(phone=normalized)

    # Сохраняем телефон в профиле (Фича 1)
    user_id = str(message.from_user.id)
    await update_user_field(user_id, "phone", normalized)

    await state.set_state(OrderForm.address)
    await message.answer("Введите адрес объекта:", reply_markup=cancel_kb())


@dp.message(OrderForm.address)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    if not address:
        await message.answer("Адрес не может быть пустым. Введите адрес:")
        return
    await state.update_data(address=address)
    await state.set_state(OrderForm.comment)
    await message.answer(
        "Напишите комментарий к заказу:\n"
        "<i>(или нажмите «⏭️ Пропустить»)</i>",
        reply_markup=skip_inline_kb()
    )


@dp.message(OrderForm.comment)
async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text.strip()
    if comment.lower() in ("пропустить", "нет", "-", "без комментария"):
        comment = "—"

    await state.update_data(comment=comment)
    await state.set_state(OrderForm.photo)
    await message.answer(
        "📸 Прикрепите фото объекта (необязательно):\n"
        "<i>Или нажмите «⏭️ Пропустить»</i>",
        reply_markup=skip_inline_kb()
    )


@dp.callback_query(F.data == "skip_field", StateFilter(OrderForm))
async def callback_skip_field(callback: types.CallbackQuery, state: FSMContext):
    """Обработка нажатия inline-кнопки 'Пропустить'."""
    current_state = await state.get_state()
    
    if current_state == "OrderForm:comment":
        await state.update_data(comment="—")
        await state.set_state(OrderForm.photo)
        await callback.message.edit_text("📸 Прикрепите фото объекта (необязательно):")
        await callback.message.answer("⏭️ Комментарий пропущен. Отправьте фото или нажмите «Пропустить».", reply_markup=skip_inline_kb())
    elif current_state == "OrderForm:photo":
        await state.update_data(photo_file_id=None)
        await callback.message.edit_text("📸 Фото пропущено")
        await finalize_order(callback.message, state)
    
    await callback.answer()


# ─── Фича 4: Фото к заказу ──────────────────────────────────────────────────
@dp.message(OrderForm.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    """Сохраняем file_id фото в данные заказа."""
    photo = message.photo[-1]  # лучшее качество
    await state.update_data(photo_file_id=photo.file_id)
    await finalize_order(message, state)


@dp.message(OrderForm.photo)
async def skip_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_file_id=None)
    await finalize_order(message, state)


async def finalize_order(message: types.Message, state: FSMContext):
    """Финальная обработка заказа."""
    data = await state.get_data()

    category = SERVICE_CATEGORIES.get(data.get("category", ""), "Общее")
    name = data.get("name", "—")
    phone = data.get("phone", "—")
    address = data.get("address", "—")
    comment = data.get("comment", "—")
    photo_file_id = data.get("photo_file_id")

    summary = (
        f"📦 <b>Новый заказ</b> | {category}\n"
        f"👤 Имя: {name}\n"
        f"📱 Телефон: {phone}\n"
        f"📍 Адрес: {address}\n"
        f"💬 Комментарий: {comment}\n"
        f"🆔 Клиент: {message.from_user.full_name} (id: <code>{message.from_user.id}</code>)"
    )

    # Уведомляем администратора
    if ADMIN_ID is not None:
        try:
            if photo_file_id:
                await bot.send_photo(ADMIN_ID, photo_file_id, caption=summary)
            else:
                await bot.send_message(ADMIN_ID, summary)
        except Exception as e:
            logger.error(f"❌ Не удалось уведомить админа: {e}")
    else:
        logger.warning("⚠️ ADMIN_ID не задан")

    # Логируем заказ
    async with aiofiles.open(ORDER_LOG, "a", encoding="utf-8") as f:
        await f.write(summary + "\n\n")

    # Создаём задачу в YouGile
    try:
        task = create_task(
            title=f"Заказ: {category} — {name}",
            description=summary
        )
        task_id = task.get("id", "—")

        # Сохраняем ID заказа в профиле
        user_id = str(message.from_user.id)
        await update_user_field(user_id, "last_order_id", task_id)

        # Сохраняем имя в профиле
        await update_user_field(user_id, "full_name", name)

        # Сохраняем адрес в профиле
        await update_user_field(user_id, "last_address", address)

        response_text = (
            f"✅ Спасибо! Ваш заказ принят и добавлен в YouGile.\n"
            f"📋 ID задачи: <code>{task_id}</code>\n"
            f"📝 Название: {task.get('title', '—')}"
        )
    except Exception as e:
        logger.exception("❌ Ошибка при создании задачи в YouGile")
        response_text = (
            f"⚠️ Заказ принят, но ошибка в YouGile: {e}\n"
            f"Менеджер свяжется с вами вручную."
        )

    users = await load_users()
    user_data = users.get(str(message.from_user.id), {})
    await message.answer(response_text, reply_markup=main_menu_kb_with_admin(str(message.from_user.id), user_data))
    await state.clear()


@dp.message(F.text == "❌ Отмена", StateFilter("*"))
async def cancel_order(message: types.Message, state: FSMContext):
    await state.clear()
    users = await load_users()
    user_data = users.get(str(message.from_user.id), {})
    await message.answer("Оформление заказа отменено.", reply_markup=main_menu_kb_with_admin(str(message.from_user.id), user_data))


# ─── Кнопки главного меню ──────────────────────────────────────────────────
@dp.message(F.text == "👤 Мой профиль")
async def btn_profile(message: types.Message):
    await cmd_profile(message)


@dp.message(F.text == "🛡️ Админ-панель")
async def btn_admin_panel(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer("🛡️ <b>Админ-панель</b>\nВыберите действие:", reply_markup=admin_panel_kb())


@dp.message(F.text == "🔙 Назад")
async def btn_back(message: types.Message):
    users = await load_users()
    user_data = users.get(str(message.from_user.id), {})
    user_data["_user_id"] = str(message.from_user.id)
    await message.answer("📋 Главное меню:", reply_markup=main_menu_kb_with_admin(str(message.from_user.id), user_data))


@dp.message(F.text == "👥 Пользователи")
async def btn_users(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return
    await list_users(message)


@dp.message(F.text == "📊 Статистика")
async def btn_stats(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return
    await cmd_stats(message)


@dp.message(F.text == "🔧 ТО статус")
async def btn_maintenance(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return
    await cmd_maintenance(message)


@dp.message(F.text == "📢 Рассылка")
async def btn_broadcast(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return
    await message.answer(
        "📢 <b>Режим рассылки</b>\n"
        "Отправьте сообщение, которое нужно разослать всем пользователям.\n"
        "Для отмены введите /cancel или нажмите «🔙 Назад».",
        reply_markup=admin_panel_kb()
    )
    await state.set_state(BroadcastForm.message)


@dp.message(F.text == "📥 Экспорт CSV")
async def btn_export(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ.")
        return
    await cmd_export(message)


# ─── Фича: Мои заказы (история) ─────────────────────────────────────────────
@dp.message(F.text == "📋 Мои заказы")
async def my_orders(message: types.Message):
    user_id = str(message.from_user.id)

    # Ищем в локальном логе
    try:
        async with aiofiles.open(ORDER_LOG, "r", encoding="utf-8") as f:
            log_content = await f.read()
    except Exception:
        await message.answer("⚠️ Не удалось загрузить историю заказов.")
        return

    # Извлекаем заказы пользователя
    pattern = rf"(📦 <b>Новый заказ</b>.*?id: <code>{user_id}</code>\))"
    matches = re.findall(pattern, log_content, re.DOTALL)

    if not matches:
        await message.answer("📭 У вас пока нет заказов.\nНажмите «🧾 Сделать заказ», чтобы оформить.")
        return

    # Показываем последние 3
    last_orders = matches[-3:]
    for i, order in enumerate(reversed(last_orders)):
        # Чистим HTML для читаемости
        clean = order.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
        header = f"📋 <b>Заказ #{len(matches) - i}</b>" if i < 2 else f"📋 <b>Последний заказ</b>"
        await message.answer(f"{header}\n\n{clean}")


# ─── Обработка любых сообщений в FSM (подсказка) ────────────────────────────
@dp.message(StateFilter(OrderForm))
async def handle_unexpected_in_form(message: types.Message):
    await message.answer(
        "Пожалуйста, следуйте инструкциям бота.\n"
        "Для отмены нажмите «❌ Отмена»."
    )


# ═════════════════════════════════════════════════════════════════════════════
# ─── Админ: список пользователей ────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@dp.message(Command("users"))
async def list_users(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⛔ Только админ может просматривать список.")
        return

    users = await load_users()
    if not users:
        await message.answer("👥 Пока никто не подключился к боту.")
        return

    def get_joined(data):
        if isinstance(data, dict):
            return data.get("joined", "1970-01-01T00:00:00")
        return data

    sorted_users = sorted(users.items(), key=lambda x: get_joined(x[1]))
    PAGE_SIZE = 50
    pages = [sorted_users[i:i + PAGE_SIZE] for i in range(0, len(sorted_users), PAGE_SIZE)]

    for page_idx, page_users in enumerate(pages):
        text = f"👥 Всего пользователей: <b>{len(users)}</b>"
        if len(pages) > 1:
            text += f" (стр. {page_idx + 1}/{len(pages)})"
        text += "\n\n"

        for uid, data in page_users:
            if isinstance(data, dict):
                username = data.get("username")
                full_name = data.get("full_name")
                phone = data.get("phone", "—")
                address = data.get("last_address", "—")
                joined = data.get("joined", "—")
                ratings = data.get("ratings", [])
                avg_rating = f"{sum(ratings)/len(ratings):.1f}⭐" if ratings else "—"

                if username:
                    name_display = f"@{username}"
                elif full_name:
                    name_display = full_name
                else:
                    name_display = "❓"
            else:
                name_display = "❓"
                phone = "—"
                address = "—"
                joined = str(data)
                avg_rating = "—"

            text += f"• <b>{name_display}</b>\n"
            text += f"  ID: <code>{uid}</code> | 📱 {phone}\n"
            text += f"  📍 Адрес: {address}\n"
            text += f"  ⭐ {avg_rating} | 📅 {joined}\n\n"

        await message.answer(text)


# ═════════════════════════════════════════════════════════════════════════════
# ─── Цикл напоминаний ───────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

def calc_next_maintenance(joined_str: str, last_maintenance_str: str = None) -> datetime | None:
    """Вычисляет следующую дату ТО."""
    if last_maintenance_str:
        try:
            last_maint = datetime.fromisoformat(last_maintenance_str)
            return last_maint + timedelta(days=MAINTENANCE_INTERVAL_MONTHS * 30)
        except (ValueError, TypeError):
            pass
    if not joined_str:
        return None
    try:
        joined_at = datetime.fromisoformat(joined_str)
        return joined_at + timedelta(days=MAINTENANCE_INTERVAL_MONTHS * 30)
    except (ValueError, TypeError):
        return None


async def send_maintenance_reminder(user_id: str, user_data: dict, next_maint: datetime):
    """Отправляет напоминание пользователю."""
    days_left = (next_maint - datetime.now()).days
    if days_left <= 0:
        text = (
            "🔧 <b>Напоминание о ТО</b>\n\n"
            "Прошло 6 месяцев с момента последнего обслуживания. "
            "Рекомендуем провести техническое обслуживание скважины, "
            "чтобы всё работало как часы.\n\n"
            "Нажмите 🧾 Сделать заказ, чтобы записаться."
        )
    else:
        text = (
            "📅 <b>Плановое ТО</b>\n\n"
            f"Через {days_left} дн. ({next_maint.strftime('%d.%m.%Y')}) рекомендуется провести ТО скважины.\n\n"
            "Нажмите 🧾 Сделать заказ, чтобы записаться заранее."
        )
    try:
        await bot.send_message(int(user_id), text)
        return True
    except Exception as e:
        logger.warning(f"Не удалось отправить напоминание {user_id}: {e}")
        return False


async def notify_admin_maintenance(admin_id: int, user_id: str, user_data: dict, next_maint: datetime, status: str):
    """Уведомляет админа о статусе ТО пользователя."""
    name = user_data.get("full_name", "—")
    phone = user_data.get("phone", "—")
    days_left = (next_maint - datetime.now()).days

    text = (
        f"🔧 <b>ТО пользователя</b>\n\n"
        f"👤 {name} ({user_id})\n"
        f"📱 {phone}\n"
        f"📆 Дата ТО: {next_maint.strftime('%d.%m.%Y')}\n"
        f"📌 Статус: {status}\n"
        f"⏰ Осталось: {days_left} дн."
    )
    try:
        await bot.send_message(admin_id, text)
        return True
    except Exception as e:
        logger.warning(f"Не удалось уведомить админа о ТО {user_id}: {e}")
        return False


async def reminder_loop():
    """Проверка напоминаний о ТО каждый час.
    
    Логика:
    - За 7 дней до ТО → напоминание пользователю + уведомление админу
    - В день ТО (0 дней) → напоминание пользователю + уведомление админу
    - После ТО (просрочено) → напоминание пользователю + уведомление админу
    - После напоминания → сброс через 30 дней (следующий цикл)
    """
    while True:
        try:
            now = datetime.now()
            users = await load_users()
            changed = False
            admin_notifications = []

            for user_id, user_data in list(users.items()):
                if not isinstance(user_data, dict):
                    continue

                # Пропускаем самого админа
                if str(user_id) == str(ADMIN_ID):
                    continue

                joined_str = user_data.get("joined")
                if not joined_str:
                    continue

                # Дата последнего напоминания или None
                last_reminder = user_data.get("last_reminder_sent")
                next_maint = calc_next_maintenance(joined_str, last_reminder)
                if not next_maint:
                    continue

                days_until = (next_maint - now).days
                last_reminder_date = user_data.get("last_reminder_sent")

                # Проверяем, не отправляли ли напоминание в последние 30 дней
                should_remind = False
                status_text = ""

                if last_reminder_date:
                    try:
                        last_dt = datetime.fromisoformat(last_reminder_date)
                        days_since_reminder = (now - last_dt).days
                        if days_since_reminder < 30:
                            continue  # Не беспокоим слишком часто
                    except (ValueError, TypeError):
                        pass

                if days_until <= -30:
                    # Просрочено более чем на 30 дней — повторяем напоминание
                    should_remind = True
                    status_text = "🔴 ТО просрочено"
                elif days_until <= 0:
                    # День ТО или просрочено
                    should_remind = True
                    status_text = f"🔴 ТО сегодня/просрочено ({abs(days_until)} дн.)"
                elif days_until <= 7:
                    # За неделю до ТО
                    should_remind = True
                    status_text = f"🟡 ТО через {days_until} дн."

                if should_remind:
                    # Отправляем пользователю
                    user_sent = await send_maintenance_reminder(user_id, user_data, next_maint)
                    
                    # Формируем уведомление админу
                    if user_sent:
                        users[user_id]["last_reminder_sent"] = now.isoformat()
                        changed = True
                        admin_notifications.append(
                            (user_id, user_data, next_maint, status_text)
                        )
                        logger.info(f"✅ Напоминание о ТО → {user_id} ({status_text})")

            # Уведомляем админа списком
            if admin_notifications:
                report = f"🔧 <b>Напоминания о ТО</b> ({len(admin_notifications)}):\n\n"
                for uid, udata, maint, status in admin_notifications:
                    name = udata.get("full_name", "—")
                    phone = udata.get("phone", "—")
                    report += f"• {name} | {phone} | {status} | {maint.strftime('%d.%m.%Y')}\n"
                
                await bot.send_message(int(ADMIN_ID), report)
                logger.info(f"📋 Отчёт админу о ТО: {len(admin_notifications)} уведомлений")

            if changed:
                await save_users(users)

        except Exception as e:
            logger.error(f"❌ Ошибка в цикле напоминаний: {e}")

        await asyncio.sleep(3600)  # Проверка каждый час


# ═════════════════════════════════════════════════════════════════════════════
# ─── FastAPI вебхук ─────────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌐 FastAPI сервер запущен")
    yield
    logger.info("🌐 FastAPI сервер остановлен")


app = FastAPI(lifespan=lifespan)


@app.post("/yougile/webhook")
async def yougile_webhook(request: Request):
    """Принимает вебхуки от YouGile с проверкой секрета."""
    if YOUGILE_WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Yougile-Secret")
        if not secret_header:
            raise HTTPException(status_code=401, detail="Missing secret header")
        if secret_header != YOUGILE_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if ADMIN_ID is not None:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔔 Событие из YouGile:\n<pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить событие: {e}")

    return {"status": "ok"}


@app.get("/health")
async def health_check():
    """Эндпоинт для проверки работоспособности."""
    return {"status": "ok"}


# ═════════════════════════════════════════════════════════════════════════════
# ─── Graceful Shutdown ─────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

async def graceful_shutdown():
    """Корректная остановка бота."""
    logger.info("🛑 Получен сигнал остановки...")

    try:
        users = await load_users()
        await save_users(users)
        logger.info("✅ Данные пользователей сохранены")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении данных: {e}")

    try:
        await bot.session.close()
        logger.info("✅ Сессия бота закрыта")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии сессии: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# ─── Главная точка входа ───────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

async def main():
    logger.info("✅ Бот запускается: Telegram + FastAPI + 9 новых фич")
    check_startup()

    await migrate_old_format()

    # Обработчики сигналов (только Unix)
    loop = asyncio.get_event_loop()
    if os.name != "nt":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(graceful_shutdown()))

    reminder_task = asyncio.create_task(reminder_loop())

    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    try:
        await asyncio.gather(
            dp.start_polling(bot),
            server.serve(),
        )
    except asyncio.CancelledError:
        logger.info("⚠️ Получен сигнал отмены")
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
