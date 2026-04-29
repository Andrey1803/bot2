import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла (для локальной разработки)
load_dotenv()


def _get_env(name: str, required: bool = True) -> str | None:
    """Получить переменную окружения. Если required=True и нет — упасть с ошибкой."""
    value = os.getenv(name)
    if required and (value is None or value.strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# Обязательные параметры
API_TOKEN = _get_env("API_TOKEN")
YOUGILE_API_KEY = _get_env("YOUGILE_API_KEY")
COLUMN_ID = _get_env("COLUMN_ID")

# Необязательные параметры
ADMIN_ID = None
_admin_id = os.getenv("ADMIN_ID")
if _admin_id and _admin_id.strip():
    if _admin_id.strip().isdigit():
        ADMIN_ID = int(_admin_id.strip())
    else:
        raise ValueError(f"ADMIN_ID must be a number, got: {_admin_id}")

PROJECT_ID = os.getenv("PROJECT_ID")
BOARD_ID = os.getenv("BOARD_ID", "")

# Секрет для проверки вебхуков от YouGile
YOUGILE_WEBHOOK_SECRET = os.getenv("YOUGILE_WEBHOOK_SECRET", "")

# Интеграция с «Диспетчер задач» (опционально)
DISPATCHER_API_URL = os.getenv("DISPATCHER_API_URL", "").strip().rstrip("/")
DISPATCHER_INBOUND_API_KEY = os.getenv("DISPATCHER_INBOUND_API_KEY", "").strip()
DISPATCHER_GROUP_ID = os.getenv("DISPATCHER_GROUP_ID", "").strip()
DISPATCHER_COMPANY_NAME = os.getenv("DISPATCHER_COMPANY_NAME", "").strip()
DISPATCHER_GROUP_NAME = os.getenv("DISPATCHER_GROUP_NAME", "").strip()
