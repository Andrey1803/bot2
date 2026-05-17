# tests/test_yougile.py
import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("YOUGILE_API_URL", "https://yougile.com/api-v2")
API_KEY = os.getenv("YOUGILE_API_KEY")
AUTH_MODE = os.getenv("YOUGILE_AUTH_MODE", "ApiKey")  # ApiKey или Bearer


async def test_yougile():
    headers = {"Content-Type": "application/json"}

    if AUTH_MODE.lower() == "bearer":
        headers["Authorization"] = f"Bearer {API_KEY}"
    else:
        headers["X-Api-Key"] = API_KEY

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/projects", headers=headers) as resp:
            print("Status:", resp.status)
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            print("Response:", data)


if __name__ == "__main__":
    asyncio.run(test_yougile())
