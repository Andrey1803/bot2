import requests
from config import YOUGILE_API_KEY, COLUMN_ID

API_URL = "https://yougile.com/api-v2"


def _headers():
    """Заголовки для запросов к YouGile API."""
    return {
        "Authorization": f"Bearer {YOUGILE_API_KEY}",
        "Content-Type": "application/json",
    }


def create_task(title: str, description: str = ""):
    """
    Создаёт задачу в YouGile в указанной колонке.
    """
    url = f"{API_URL}/tasks"
    payload = {
        "title": title.strip() or "Новый заказ",
        "description": description or "",
        "columnId": COLUMN_ID,
    }
    response = requests.post(url, headers=_headers(), json=payload)
    if response.status_code in (200, 201):
        return response.json()
    else:
        raise Exception(f"{response.status_code} {response.text}")


def search_tasks_by_user(user_id: str, limit: int = 10) -> list:
    """
    Ищет задачи по ID пользователя в описании.
    Возвращает список задач, отсортированных по дате (новые сверху).
    """
    url = f"{API_URL}/tasks"
    params = {"limit": limit}
    response = requests.get(url, headers=_headers(), params=params)
    if response.status_code in (200, 201):
        data = response.json()
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        # Фильтруем задачи по ID пользователя
        return [t for t in tasks if f"id: {user_id}" in t.get("description", "") or f"id:{user_id}" in t.get("description", "")]
    else:
        raise Exception(f"{response.status_code} {response.text}")


def get_task_status(task_id: str) -> dict:
    """
    Получает информацию о задаче (статус, колонка и т.д.).
    """
    url = f"{API_URL}/tasks/{task_id}"
    response = requests.get(url, headers=_headers())
    if response.status_code in (200, 201):
        return response.json()
    else:
        raise Exception(f"{response.status_code} {response.text}")


def get_tasks_for_stats(days: int = 30) -> list:
    """
    Получает все задачи с доски для статистики.
    """
    url = f"{API_URL}/tasks"
    params = {"limit": 500}
    response = requests.get(url, headers=_headers(), params=params)
    if response.status_code in (200, 201):
        data = response.json()
        return data if isinstance(data, list) else data.get("tasks", [])
    else:
        raise Exception(f"{response.status_code} {response.text}")


def get_all_board_tasks(board_id: str) -> list:
    """
    Получает все задачи. YouGile API v2 может не поддерживать листинг.
    Пробуем все известные эндпоинты.
    """
    from config import COLUMN_ID
    import logging
    logger = logging.getLogger(__name__)
    
    all_tasks = []
    seen_ids = set()
    
    urls_to_try = [
        f"{API_URL}/tasks",
        f"{API_URL}/columns/{COLUMN_ID}/tasks",
        f"{API_URL}/tasks?limit=100",
    ]
    
    for url in urls_to_try:
        try:
            response = requests.get(url, headers=_headers(), timeout=10)
            logger.info(f"🔍 YouGile GET {url} → {response.status_code}")
            if response.status_code in (200, 201):
                data = response.json()
                logger.info(f"📋 Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                tasks = data if isinstance(data, list) else data.get("tasks", data.get("items", data.get("columns", [])))
                if isinstance(tasks, list):
                    for t in tasks:
                        tid = t.get("id")
                        if tid and tid not in seen_ids:
                            all_tasks.append(t)
                            seen_ids.add(tid)
                    logger.info(f"✅ Found {len(all_tasks)} tasks via {url}")
                    if len(all_tasks) > 0:
                        return all_tasks
                elif isinstance(tasks, dict):
                    logger.info(f"📋 Tasks dict keys: {list(tasks.keys())}")
        except Exception as e:
            logger.warning(f"❌ Failed {url}: {e}")
            continue
    
    return all_tasks


def get_column_name(column_id: str) -> str:
    """
    Получает название колонки по ID.
    """
    url = f"{API_URL}/columns/{column_id}"
    response = requests.get(url, headers=_headers())
    if response.status_code in (200, 201):
        data = response.json()
        return data.get("title", column_id)
    return column_id
