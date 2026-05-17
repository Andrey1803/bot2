# tests/test_create_task.py
import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("YOUGILE_API_URL", "https://yougile.com/api-v2")
API_KEY = os.getenv("YOUGILE_API_KEY")
PROJECT_ID = os.getenv("YOUGILE_PROJECT_ID")
COLUMN_ID = os.getenv("YOUGILE_COLUMN_ID")
AUTH_MODE = os.getenv("YOUGILE_AUTH_MODE", "ApiKey")  # ApiKey или Bearer


async def test_create_task():
    headers = {"Content-Type": "application/json"}
    if AUTH_MODE.lower() == "bearer":
        headers["Authorization"] = f"Bearer {API_KEY}"
    else:
        headers["X-Api-Key"] = API_KEY

    payload = {
        "columnId": COLUMN_ID,
        "title": "Тестовая заявка",
        "description": (
            "Имя: Андрей\n"
            "Телефон: +375 29 123-45-67\n"
            "Адрес: Минск, ул. Победы 10\n"
            "Тип: Ремонт\n"
            "Проблема: Не работает кондиционер\n\n"
            "Telegram ID: 123456789\n"
            "Username: @andrey_dev"
        )
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/tasks", headers=headers, json=payload) as resp:
            print("Status:", resp.status)
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            print("Response:", data)


if __name__ == "__main__":
    asyncio.run(test_create_task())
