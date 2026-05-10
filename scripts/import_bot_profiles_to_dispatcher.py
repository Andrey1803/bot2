#!/usr/bin/env python3
"""
Одноразово создаёт в «Диспетчер задач» по одной задаче на клиента из data/users.json
с планом ТО (как в боте: от даты joined + 6×30 дней).

Зачем: напоминания ТО жили только в боте; диспетчер их не видел. Этот скрипт — перенос «карточек».

Подготовка (как у бота на Railway, можно скопировать в .env рядом со скриптом или экспортировать в shell):
  DISPATCHER_API_URL, DISPATCHER_INBOUND_API_KEY,
  DISPATCHER_GROUP_ID или DISPATCHER_COMPANY_NAME (+ опционально DISPATCHER_GROUP_NAME)

Запуск из корня репозитория бота:
  python scripts/import_bot_profiles_to_dispatcher.py          # только показать, что создастся
  python scripts/import_bot_profiles_to_dispatcher.py --apply  # создать задачи
  python scripts/import_bot_profiles_to_dispatcher.py --apply --limit 3

Внимание: каждый запуск с --apply создаёт НОВЫЕ задачи. Не гоняйте дважды на одних и тех же данных.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# корень репозитория → подхватить config как у бота
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    pass

from tools.dispatcher_api import initial_status_for_maintenance_next_due


def _next_to_ymd(joined_str: str | None) -> str | None:
    """Как calc_next_maintenance в main.py (без last_maintenance): joined + 6×30 дней."""
    if not joined_str or not str(joined_str).strip():
        return None
    try:
        joined_at = datetime.fromisoformat(str(joined_str).strip())
        nxt = joined_at + timedelta(days=6 * 30)
        return nxt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _load_users(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Нет файла: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_payload(uid: str, data: dict) -> dict | None:
    phone = (data.get("phone") or "").strip()
    if not phone or phone == "—":
        return None
    name = (data.get("full_name") or "").strip() or f"tg {uid}"
    address = (data.get("last_address") or "").strip() or "—"
    next_ymd = _next_to_ymd(data.get("joined"))
    if not next_ymd:
        return None

    title = f"ТО (из бота): {name}"[:500]
    note = (
        f"Импорт из users.json. Telegram id: {uid}\n"
        f"Дата следующего ТО по правилам бота: {next_ymd}\n"
        "Не удаляйте без нужды — это связка с напоминаниями в боте."
    )[:4000]

    payload: dict = {
        "title": title,
        "contactName": name,
        "customerPhone": phone,
        "objectAddress": address,
        "externalSource": "telegram-import",
        "externalRef": f"tg:{uid}",
        "note": note,
        "maintenanceEnabled": True,
        "maintenanceIntervalMonths": 6,
        "maintenanceNextDueYmd": next_ymd,
        "maintenanceNote": "Перенесено из бота (joined + 6 мес.×30 дн.)",
        "initialStatus": initial_status_for_maintenance_next_due(next_ymd),
    }
    gid = (os.getenv("DISPATCHER_GROUP_ID") or "").strip()
    company = (os.getenv("DISPATCHER_COMPANY_NAME") or "").strip()
    if gid:
        payload["groupId"] = gid
    elif company:
        payload["companyName"] = company
        gn = (os.getenv("DISPATCHER_GROUP_NAME") or "").strip()
        if gn:
            payload["groupName"] = gn
    else:
        raise SystemExit("Нужен DISPATCHER_GROUP_ID или DISPATCHER_COMPANY_NAME в окружении")
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--users",
        type=Path,
        default=ROOT / "data" / "users.json",
        help="Путь к users.json",
    )
    ap.add_argument("--apply", action="store_true", help="Реально отправить POST (иначе только печать)")
    ap.add_argument("--limit", type=int, default=0, help="Максимум записей (0 = без лимита)")
    args = ap.parse_args()

    base = (os.getenv("DISPATCHER_API_URL") or "").strip().rstrip("/")
    key = (os.getenv("DISPATCHER_INBOUND_API_KEY") or "").strip()
    if not base or not key:
        raise SystemExit("Задайте DISPATCHER_API_URL и DISPATCHER_INBOUND_API_KEY")
    if len(key) < 16:
        raise SystemExit("DISPATCHER_INBOUND_API_KEY слишком короткий")

    users = _load_users(args.users)
    url = f"{base}/v1/integration/inbound-order"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    shown = 0
    for uid, data in users.items():
        if not isinstance(data, dict):
            continue
        if data.get("blocked"):
            continue
        payload = _build_payload(str(uid), data)
        if not payload:
            print(f"SKIP {uid}: нет телефона или даты joined")
            continue
        if args.limit and shown >= args.limit:
            break
        shown += 1
        print(f"{'POST' if args.apply else 'DRY'} {uid} → {payload['title'][:60]}… ТО {payload['maintenanceNextDueYmd']}")
        if args.apply:
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            if r.status_code not in (200, 201):
                print(f"  ERROR {r.status_code}: {(r.text or '')[:500]}")
            else:
                j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                print(f"  ok taskId={j.get('taskId')}")


if __name__ == "__main__":
    main()
