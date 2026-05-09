import logging
from typing import Any

import requests

from config import (
    DISPATCHER_API_URL,
    DISPATCHER_COMPANY_NAME,
    DISPATCHER_GROUP_ID,
    DISPATCHER_GROUP_NAME,
    DISPATCHER_INBOUND_API_KEY,
)

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(DISPATCHER_API_URL and DISPATCHER_INBOUND_API_KEY)


def send_order_to_dispatcher(
    *,
    category: str,
    name: str,
    phone: str,
    address: str,
    comment: str,
    telegram_user_id: str,
    telegram_full_name: str,
) -> dict[str, Any]:
    """
    Отправляет заказ в API «Диспетчер задач».
    Не бросает исключения наружу для пользовательского флоу.
    Возвращает словарь с ключами ok, skipped, taskId, error (для логов и уведомления админа).
    """
    if not _enabled():
        return {"ok": False, "skipped": True, "reason": "dispatcher_env_missing", "taskId": None, "error": None}

    title = f"Заказ: {category} — {name}".strip()[:500] or "Новый заказ из Telegram"
    note = (
        f"Клиент: {telegram_full_name} (tg id: {telegram_user_id})\n"
        f"Комментарий: {comment or '—'}\n"
        f"Источник: Telegram bot"
    )
    payload: dict[str, Any] = {
        "title": title,
        "contactName": name or "",
        "customerPhone": phone or "",
        "objectAddress": address or "",
        "externalSource": "telegram",
        "externalRef": f"tg:{telegram_user_id}",
        "note": note,
    }
    if DISPATCHER_GROUP_ID:
        payload["groupId"] = DISPATCHER_GROUP_ID
    elif DISPATCHER_COMPANY_NAME:
        payload["companyName"] = DISPATCHER_COMPANY_NAME
        if DISPATCHER_GROUP_NAME:
            payload["groupName"] = DISPATCHER_GROUP_NAME
    else:
        logger.warning(
            "Dispatcher integration enabled but route is undefined: set DISPATCHER_GROUP_ID or DISPATCHER_COMPANY_NAME",
        )
        return {"ok": False, "skipped": True, "reason": "no_group_or_company", "taskId": None, "error": None}

    url = f"{DISPATCHER_API_URL}/v1/integration/inbound-order"
    headers = {
        "Authorization": f"Bearer {DISPATCHER_INBOUND_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code in (200, 201):
            data = resp.json()
            if isinstance(data, dict):
                tid = data.get("taskId")
                logger.info("Dispatcher task created: %s", tid)
                return {"ok": True, "skipped": False, "taskId": tid, "groupId": data.get("groupId"), "error": None, "raw": data}
            logger.error("Dispatcher API: unexpected JSON shape: %s", str(data)[:300])
            return {"ok": False, "skipped": False, "taskId": None, "error": "invalid_json_shape"}
        err_text = (resp.text or "")[:800]
        logger.error("Dispatcher API error: %s %s", resp.status_code, err_text)
        return {
            "ok": False,
            "skipped": False,
            "taskId": None,
            "error": f"HTTP {resp.status_code}: {err_text}",
            "status_code": resp.status_code,
        }
    except Exception as err:
        logger.exception("Dispatcher request failed: %s", err)
        return {"ok": False, "skipped": False, "taskId": None, "error": str(err)}
