import os

def _get_env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and (value is None or value.strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# 🔑 Telegram
API_TOKEN = _get_env("API_TOKEN")
_admin_id = os.getenv("ADMIN_ID")
ADMIN_ID = int(_admin_id) if _admin_id and _admin_id.isdigit() else None

# 📊 Yougile
API_URL = os.getenv("YOUGILE_API_URL", "https://yougile.com/api-v2")
API_KEY = _get_env("YOUGILE_API_KEY")
PROJECT_ID = _get_env("PROJECT_ID")
COLUMN_ID = _get_env("COLUMN_ID")
AUTH_MODE = os.getenv("YOUGILE_AUTH_MODE", "ApiKey")

# 🌐 Прокси (опционально)
PROXY_URL = os.getenv("PROXY_URL")
