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
) -> dict[str, Any] | None:
    """
    Отправляет заказ в API «Диспетчер задач».
    Не бросает исключения наружу для пользовательского флоу.
    """
    if not _enabled():
        return None

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
        return None

    url = f"{DISPATCHER_API_URL}/v1/integration/inbound-order"
    headers = {
        "Authorization": f"Bearer {DISPATCHER_INBOUND_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code in (200, 201):
            data = resp.json()
            logger.info("Dispatcher task created: %s", data.get("taskId"))
            return data
        logger.error("Dispatcher API error: %s %s", resp.status_code, resp.text[:500])
    except Exception as err:
        logger.exception("Dispatcher request failed: %s", err)
    return None
