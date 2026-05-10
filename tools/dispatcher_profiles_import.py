"""Создание в диспетчере карточек ТО по профилям из users.json (без ручного скрипта)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from config import (
    DISPATCHER_AUTO_SYNC_MAINTENANCE,
    DISPATCHER_COMPANY_NAME,
    DISPATCHER_GROUP_ID,
    DISPATCHER_GROUP_NAME,
    DISPATCHER_INBOUND_INITIAL_STATUS,
    DISPATCHER_MAINTENANCE_INTERVAL_MONTHS,
    DISPATCHER_MAINTENANCE_NOTE,
    DISPATCHER_MAINTENANCE_PLAN,
)
from tools.dispatcher_api import (
    build_external_ref,
    dispatcher_inbound_ready,
    post_inbound_order_payload,
)

logger = logging.getLogger(__name__)

# Сохраняется в users.json после успешного POST — повторные старты не дублируют задачи.
FIELD_DISPATCHER_MAINT_TASK_ID = "dispatcher_maint_task_id"


def should_run_startup_sync() -> bool:
    return (
        DISPATCHER_AUTO_SYNC_MAINTENANCE
        and DISPATCHER_MAINTENANCE_PLAN
        and dispatcher_inbound_ready()
    )


def sync_missing_maintenance_dispatcher_cards(
    users: dict[str, Any],
    calc_next_maintenance: Callable[..., datetime | None],
) -> dict[str, Any]:
    """
    Синхронно: для каждого пользователя с телефоном и датой ТО, без dispatcher_maint_task_id,
    создаёт задачу с планом ТО. Мутирует записи users. Возвращает счётчики.
    """
    if not should_run_startup_sync():
        return {"ran": False, "created": 0, "failed": 0, "skipped_users": 0}

    created = 0
    failed = 0
    skipped = 0

    for uid, data in list(users.items()):
        if not isinstance(data, dict) or data.get("blocked"):
            skipped += 1
            continue
        if data.get(FIELD_DISPATCHER_MAINT_TASK_ID):
            continue

        phone = (data.get("phone") or "").strip()
        if not phone or phone == "—":
            skipped += 1
            continue

        joined = data.get("joined")
        last_r = data.get("last_reminder_sent")
        next_dt = calc_next_maintenance(joined, last_r)
        if not next_dt:
            skipped += 1
            continue

        next_ymd = next_dt.strftime("%Y-%m-%d")
        name = (data.get("full_name") or "").strip() or f"tg {uid}"
        address = (data.get("last_address") or "").strip() or "—"
        title = f"ТО (из бота): {name}"[:500]
        note = (
            f"Авто-синхрон из бота. Telegram id: {uid}\n"
            f"Следующее ТО (как в напоминаниях бота): {next_ymd}"
        )[:4000]

        im = DISPATCHER_MAINTENANCE_INTERVAL_MONTHS
        payload: dict[str, Any] = {
            "title": title,
            "contactName": name,
            "customerPhone": phone,
            "objectAddress": address,
            "externalSource": "telegram-maintenance-sync",
            "externalRef": build_external_ref(str(uid), address),
            "note": note,
            "maintenanceEnabled": True,
            "maintenanceIntervalMonths": im,
            "maintenanceNextDueYmd": next_ymd,
        }
        mn = (DISPATCHER_MAINTENANCE_NOTE or "").strip()
        payload["maintenanceNote"] = mn if mn else "Карточка ТО синхронизирована из бота"

        if DISPATCHER_GROUP_ID:
            payload["groupId"] = DISPATCHER_GROUP_ID
        else:
            payload["companyName"] = DISPATCHER_COMPANY_NAME
            if DISPATCHER_GROUP_NAME:
                payload["groupName"] = DISPATCHER_GROUP_NAME

        st0 = DISPATCHER_INBOUND_INITIAL_STATUS.upper()
        if st0 in ("PRELIMINARY", "OPEN"):
            payload["initialStatus"] = st0

        res = post_inbound_order_payload(payload, timeout_sec=30)
        tid = res.get("taskId") if res.get("ok") else None
        if tid:
            data[FIELD_DISPATCHER_MAINT_TASK_ID] = str(tid)
            created += 1
            logger.info("Dispatcher ТО-карточка: uid=%s taskId=%s", uid, tid)
        else:
            failed += 1
            logger.warning(
                "Dispatcher ТО-синхрон: uid=%s err=%s",
                uid,
                (res.get("error") or res.get("reason") or res)[:400],
            )

    return {"ran": True, "created": created, "failed": failed, "skipped_users": skipped}
