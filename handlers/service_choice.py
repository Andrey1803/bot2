from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import db
import yougile_api
from .create_task import TaskForm
from .registration import user_menu_keyboard

router = Router()


@router.message(Command("service"))
async def choose_service(message: types.Message):
    await message.answer("🔧 Выберите тип услуги:", reply_markup=user_menu_keyboard())


@router.message(F.text == "Обслуживание")
async def service_obsluzhivanie(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
        return

    name, phone, address = user["name"], user["phone"], user.get("address", "не указан")

    try:
        # ✅ projectId и columnId подставляются внутри yougile_api
        task = await yougile_api.create_task(
            customer_name=name,
            customer_phone=phone,
            customer_address=address,
            service_type="Обслуживание",
            problem="Плановое обслуживание",
            tg_user_id=message.from_user.id,
            tg_username=message.from_user.username or "неизвестно"
        )

        # ✅ сохраняем задачу в БД вместе с task_id и task_url
        await db.save_task(
            tg_user_id=message.from_user.id,
            name=name,
            service_type="Обслуживание",
            task_id=task.get("id"),
            task_url=task.get("task_url")
        )

        await message.answer(
            f"✅ Заявка на <b>Обслуживание</b> создана!\n\n"
            f"🔗 {task.get('task_url', 'Ссылка недоступна')}",
            reply_markup=user_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании заявки: {e}")


@router.message(F.text == "Ремонт")
async def service_remont(message: types.Message, state: FSMContext):
    await state.set_state(TaskForm.problem)
    await state.update_data(service_type="Ремонт")
    await message.answer("✍️ Опишите проблему или задачу подробнее.", reply_markup=user_menu_keyboard())
