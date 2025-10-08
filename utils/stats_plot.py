import matplotlib
matplotlib.use("Agg")  # отключает GUI‑бэкенд

import aiosqlite
import matplotlib.pyplot as plt


async def plot_task_stats():
    async with aiosqlite.connect("data/database.db") as db:
        cursor = await db.execute("SELECT created_at, service_type FROM tasks")
        rows = await cursor.fetchall()

    if not rows:
        print("❌ Нет данных для графика")
        return

    daily_counts = {}
    type_counts = {}

    for created_at, service_type in rows:
        date = created_at[:10]
        daily_counts[date] = daily_counts.get(date, 0) + 1
        type_counts[service_type] = type_counts.get(service_type, 0) + 1

    # График по дням
    dates = sorted(daily_counts.keys())
    counts = [daily_counts[d] for d in dates]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, counts, marker="o")
    plt.xticks(rotation=45)
    plt.title("📈 Количество заявок по дням")
    plt.xlabel("Дата")
    plt.ylabel("Заявок")
    plt.tight_layout()
    plt.savefig("data/task_trend.png")
    plt.close()

    # График по типам
    plt.figure(figsize=(6, 4))
    plt.bar(type_counts.keys(), type_counts.values(), color="skyblue")
    plt.title("📊 Распределение по типам услуг")
    plt.xlabel("Тип услуги")
    plt.ylabel("Заявок")
    plt.tight_layout()
    plt.savefig("data/task_types.png")
    plt.close()
