from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import db
from .constants import SERVICE_TYPES
from config import ADMIN_ID   # ✅ теперь берём из config.py

router = Router()


# --- Состояния для пошаговой регистрации ---
class RegistrationForm(StatesGroup):
    name = State()
    phone = State()
    address = State()


# --- Клавиатура для пользователей ---
def user_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [types.KeyboardButton(text=stype)] for stype in SERVICE_TYPES
        ] + [[types.KeyboardButton(text="✏️ Редактировать данные")]]
    )


# --- Клавиатура для админа ---
def admin_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [types.KeyboardButton(text="👥 Количество абонентов")],
            [types.KeyboardButton(text="⏰ Ближайшие обслуживания (30 дней)")]
        ]
    )


# --- Хендлер /start ---
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Если админ → показываем админское меню
    if ADMIN_ID and user_id == ADMIN_ID:
        await message.answer("🔑 Админ-меню:", reply_markup=admin_menu_keyboard())
        return

    # Если обычный пользователь
    user = await db.get_user(user_id)
    if user:
        await message.answer(
            "✅ Вы уже зарегистрированы.\n\nТеперь выберите услугу:",
            reply_markup=user_menu_keyboard()
        )
    else:
        await state.set_state(RegistrationForm.name)
        await message.answer("👋 Добро пожаловать! Введите ваше имя:")


# --- Шаг 1: имя ---
@router.message(RegistrationForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(RegistrationForm.phone)
    await message.answer("📱 Введите ваш номер телефона:")


# --- Шаг 2: телефон ---
@router.message(RegistrationForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(RegistrationForm.address)
    await message.answer("🏠 Введите ваш адрес:")


# --- Шаг 3: адрес ---
@router.message(RegistrationForm.address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    phone = data["phone"]
    address = message.text.strip()

    # Сохраняем пользователя в БД
    await db.save_user(
        tg_user_id=message.from_user.id,
        name=name,
        phone=phone,
        address=address
    )

    await message.answer(
        f"✅ Данные сохранены!\n\n"
        f"👤 Имя: {name}\n"
        f"📱 Телефон: {phone}\n"
        f"🏠 Адрес: {address}\n\n"
        "Теперь можете выбрать услугу:",
        reply_markup=user_menu_keyboard()
    )
    await state.clear()


# --- Обработчик кнопки "Редактировать данные" (только для пользователей) ---
@router.message(lambda m: m.text == "✏️ Редактировать данные")
async def edit_user_data(message: types.Message, state: FSMContext):
    if ADMIN_ID and message.from_user.id == ADMIN_ID:
        await message.answer("ℹ️ Админам не нужно редактировать данные.")
        return
    await state.set_state(RegistrationForm.name)
    await message.answer("✏️ Введите новое имя:")
