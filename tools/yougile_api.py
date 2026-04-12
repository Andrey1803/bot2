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
    Получает все задачи с конкретной доски.
    """
    url = f"{API_URL}/tasks"
    params = {"boardId": board_id, "limit": 500}
    response = requests.get(url, headers=_headers(), params=params)
    if response.status_code in (200, 201):
        data = response.json()
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        return tasks
    else:
        raise Exception(f"{response.status_code} {response.text}")


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
