# tests/test_massive_tasks.py
import asyncio
import db


async def main():
    await db.init_db()

    for i in range(10):
        await db.save_task(
            name=f"Тестовая заявка {i+1}",
            service_type="Тест",
            tg_user_id=123456
        )
        print(f"✅ Заявка {i+1} сохранена")

    tasks = await db.get_tasks_by_user(123456)
    print(f"\n🔍 Найдено заявок: {len(tasks)}")
    for t in tasks:
        print(f"• {t[0]} | {t[1]} | {t[2][:10]}")


if __name__ == "__main__":
    asyncio.run(main())
