import calendar
import hashlib
import logging
import re
from datetime import date
from typing import Any

import requests

from config import (
    DISPATCHER_API_URL,
    DISPATCHER_COMPANY_NAME,
    DISPATCHER_EXTERNAL_REF_PER_ADDRESS,
    DISPATCHER_GROUP_ID,
    DISPATCHER_GROUP_NAME,
    DISPATCHER_INBOUND_API_KEY,
    DISPATCHER_INBOUND_INITIAL_STATUS,
    DISPATCHER_MAINTENANCE_INTERVAL_MONTHS,
    DISPATCHER_MAINTENANCE_NEXT_DUE_YMD,
    DISPATCHER_MAINTENANCE_NOTE,
    DISPATCHER_MAINTENANCE_PLAN,
)

logger = logging.getLogger(__name__)

_YMD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _local_today_ymd() -> str:
    t = date.today()
    return f"{t.year:04d}-{t.month:02d}-{t.day:02d}"


def _add_months_from_date(d: date, months: int) -> date:
    month0 = d.month - 1 + months
    year = d.year + month0 // 12
    month = month0 % 12 + 1
    last = calendar.monthrange(year, month)[1]
    day = min(d.day, last)
    return date(year, month, day)


def _add_months_ymd(ymd: str, months: int) -> str:
    raw = ymd.strip()
    m = _YMD_RE.match(raw)
    if not m:
        return ymd
    y, mo, da = int(raw[0:4]), int(raw[5:7]), int(raw[8:10])
    out = _add_months_from_date(date(y, mo, da), months)
    return f"{out.year:04d}-{out.month:02d}-{out.day:02d}"


def _normalize_address_key(addr: str) -> str:
    s = (addr or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s[:400]


def _external_ref(*, telegram_user_id: str, address: str) -> str:
    if DISPATCHER_EXTERNAL_REF_PER_ADDRESS:
        norm = _normalize_address_key(address)
        if norm and norm not in ("—", "-", "none", "нет"):
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
            return f"tg:{telegram_user_id}|{h}"
    return f"tg:{telegram_user_id}"


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
        "externalRef": _external_ref(telegram_user_id=telegram_user_id, address=address),
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

    st0 = DISPATCHER_INBOUND_INITIAL_STATUS.upper()
    if st0 in ("PRELIMINARY", "OPEN"):
        payload["initialStatus"] = st0

    if DISPATCHER_MAINTENANCE_PLAN:
        im = DISPATCHER_MAINTENANCE_INTERVAL_MONTHS
        payload["maintenanceEnabled"] = True
        payload["maintenanceIntervalMonths"] = im
        next_due = DISPATCHER_MAINTENANCE_NEXT_DUE_YMD
        if next_due and _YMD_RE.match(next_due):
            payload["maintenanceNextDueYmd"] = next_due
        else:
            payload["maintenanceNextDueYmd"] = _add_months_ymd(_local_today_ymd(), im)
        if DISPATCHER_MAINTENANCE_NOTE:
            payload["maintenanceNote"] = DISPATCHER_MAINTENANCE_NOTE

    url = f"{DISPATCHER_API_URL}/v1/integration/inbound-order"
    headers = {
        "Authorization": f"Bearer {DISPATCHER_INBOUND_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        logger.info("Dispatcher: POST inbound-order → %s", url)
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
        err_msg = err_text
        try:
            j = resp.json()
            if isinstance(j, dict) and j.get("error"):
                err_msg = str(j["error"])
        except Exception:
            pass
        logger.error("Dispatcher API error: %s %s url=%s", resp.status_code, err_msg, url)
        return {
            "ok": False,
            "skipped": False,
            "taskId": None,
            "error": f"HTTP {resp.status_code}: {err_msg}",
            "status_code": resp.status_code,
        }
    except requests.RequestException as err:
        logger.error(
            "Dispatcher RequestException %s: %s url=%s",
            type(err).__name__,
            err,
            url,
            exc_info=True,
        )
        return {"ok": False, "skipped": False, "taskId": None, "error": f"{type(err).__name__}: {err}"}
    except Exception as err:
        logger.error(
            "Dispatcher unexpected %s: %s url=%s",
            type(err).__name__,
            err,
            url,
            exc_info=True,
        )
        return {"ok": False, "skipped": False, "taskId": None, "error": str(err)}
