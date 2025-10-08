import aiohttp
import os
from datetime import datetime

from config import API_URL, API_KEY, COLUMN_ID, AUTH_MODE  # ✅ PROJECT_ID больше не нужен

LOG_FILE = "logs/yougile_log.txt"


def log(message: str):
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {message}\n")


async def create_task(customer_name, customer_phone, customer_address, service_type, problem, tg_user_id, tg_username):
    """
    Создаёт задачу в YouGile.
    - Используем только columnId
    - Авторизация ApiKey или Bearer (по .env)
    """
    if not API_KEY or not COLUMN_ID:
        log("❌ Не заданы ключи в .env")
        raise Exception("Не заданы YOUGILE_API_KEY или COLUMN_ID")

    headers = {"Content-Type": "application/json"}
    if AUTH_MODE.lower() == "bearer":
        headers["Authorization"] = f"Bearer {API_KEY}"
    else:
        headers["X-Api-Key"] = API_KEY

    payload = {
        "columnId": COLUMN_ID,   # ✅ оставляем только columnId
        "title": f"{service_type}: {customer_name}",
        "description": (
            f"Имя: {customer_name}\n"
            f"Телефон: {customer_phone or 'не указано'}\n"
            f"Адрес: {customer_address or 'не указано'}\n"
            f"Тип заявки: {service_type}\n"
            f"Описание: {problem}\n\n"
            f"Telegram ID: {tg_user_id}\n"
            f"Username: @{tg_username}"
        )
    }

    log(f"📤 Payload: {payload}")
    log(f"🔐 Headers: {headers}")

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/tasks", headers=headers, json=payload) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()

            log(f"📥 Response: {resp.status} — {data}")

            if resp.status != 201:
                raise Exception(f"Ошибка {resp.status}: {data}")

            task_id = data.get("id")
            task_url = f"https://yougile.com/task/{task_id}" if task_id else None
            log(f"✅ Задача создана: {task_url}")

            return {
                "id": task_id,
                "task_url": task_url
            }
