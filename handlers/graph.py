from aiogram import Router, types
from aiogram.filters import Command

from utils import stats_plot
from .registration import user_menu_keyboard  # ✅ меню пользователя

router = Router()


@router.message(Command("graph"))
async def cmd_graph(message: types.Message):
    await stats_plot.plot_task_stats()

    try:
        await message.answer_photo(
            photo=types.FSInputFile("data/task_trend.png"),
            caption="📈 Динамика заявок по дням"
        )
        await message.answer_photo(
            photo=types.FSInputFile("data/task_types.png"),
            caption="📊 Распределение заявок по типам услуг",
            reply_markup=user_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке графиков: {e}", reply_markup=user_menu_keyboard())
