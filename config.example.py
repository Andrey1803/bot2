# ШАБЛОН КОНФИГУРАЦИИ
# Скопируйте этот файл в config.py и заполните значениями,
# ИЛИ используйте переменные окружения / .env файл

import os
from dotenv import load_dotenv

load_dotenv()


def _get_env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and (value is None or value.strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


API_TOKEN = _get_env("API_TOKEN")
YOUGILE_API_KEY = _get_env("YOUGILE_API_KEY")
COLUMN_ID = _get_env("COLUMN_ID")

ADMIN_ID = None
_admin_id = os.getenv("ADMIN_ID")
if _admin_id and _admin_id.strip():
    if _admin_id.strip().isdigit():
        ADMIN_ID = int(_admin_id.strip())

PROJECT_ID = os.getenv("PROJECT_ID")
YOUGILE_WEBHOOK_SECRET = os.getenv("YOUGILE_WEBHOOK_SECRET", "")
