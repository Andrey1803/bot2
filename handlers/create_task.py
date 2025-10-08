from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import db
import yougile_api
from .registration import user_menu_keyboard  # ✅ меню для пользователей

router = Router()

class TaskForm(StatesGroup):
    problem = State()


@router.message(TaskForm.problem, F.text)
async def process_problem(message: types.Message, state: FSMContext):
    data = await state.get_data()
    service_type = data.get("service_type", "не указано")
    problem = message.text.strip()

    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
        await state.clear()
        return

    name, phone, address = user["name"], user["phone"], user.get("address", "не указан")

    try:
        task = await yougile_api.create_task(
            customer_name=name,
            customer_phone=phone,
            customer_address=address,
            service_type=service_type,
            problem=problem,
            tg_user_id=message.from_user.id,
            tg_username=message.from_user.username or "неизвестно"
        )
        await db.save_task(name, service_type, message.from_user.id)

        await message.answer(
            f"✅ Заявка на <b>{service_type}</b> создана!\n\n"
            f"Описание: {problem}\n\n"
            f"🔗 {task.get('task_url', 'Ссылка недоступна')}\n\n"
            "Можете выбрать следующую услугу:",
            reply_markup=user_menu_keyboard()  # ✅ меню пользователя
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании заявки: {e}")

    await state.clear()
