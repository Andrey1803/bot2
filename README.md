# YouGile Bot — Telegram-бот для приёма заказов

Telegram-бот, который принимает заказы от клиентов и автоматически создаёт задачи в YouGile.

## Возможности

- 📝 **Пошаговая форма заказа** — имя → телефон → адрес → комментарий
- 📋 **Создание задач в YouGile** — каждый заказ автоматически появляется в вашей доске
- 🔔 **Уведомления администратора** — мгновенные уведомления о новых заказах
- 👥 **Учёт пользователей** — сохраняет всех, кто запустил бота
- ⏰ **Напоминания** — автоматические напоминания через 6 месяцев
- 🔌 **Webhook от YouGile** — приём событий из YouGile через FastAPI

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <your-repo-url>
cd yougile_bot
```

### 2. Создание виртуального окружения

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка окружения

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

Обязательные переменные:
| Переменная | Описание | Где взять |
|---|---|---|
| `API_TOKEN` | Токен Telegram-бота | [@BotFather](https://t.me/BotFather) |
| `YOUGILE_API_KEY` | API-ключ YouGile | Настройки YouGile → API |
| `COLUMN_ID` | ID колонки для задач | Утилита `tools/list_columns.py` |

Необязательные:
| Переменная | Описание |
|---|---|
| `ADMIN_ID` | Telegram ID администратора для уведомлений |
| `PROJECT_ID` | ID проекта YouGile (для утилит) |
| `YOUGILE_WEBHOOK_SECRET` | Секрет для проверки вебхуков |

### 5. Запуск

```bash
python main.py
```

Бот запустит:
- **Telegram polling** — приём сообщений
- **FastAPI сервер** на порту 8000 — приём вебхуков от YouGile

## Деплой

### Docker

```bash
docker build -t yougile_bot .
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  yougile_bot
```

### Railway

1. Подключите репозиторий к [Railway](https://railway.app)
2. Добавьте переменные окружения в настройках проекта
3. Railway автоматически запустит бот через `railway.json`

## Утилиты

Все утилиты находятся в папке `tools/`.

| Утилита | Описание |
|---|---|
| `list_projects.py` | Список всех проектов в YouGile |
| `list_columns.py` | Список всех колонок в YouGile |
| `test.py` | Проверка подключения к проекту YouGile |
| `restore_users.py` | Восстановление пользователей из `orders.log` |
| `build_users_from_snapshot.py` | Восстановление из снимка |
| `merge_files.py` | Слияние `users.json` и `orders.log` из разных источников |

Запуск:
```bash
python tools/list_projects.py
```

## Структура проекта

```
yougile_bot/
├── main.py              # Бот + FastAPI + напоминания
├── config.py            # Конфигурация (через .env)
├── config.example.py    # Шаблон конфигурации
├── requirements.txt     # Зависимости
├── Dockerfile           # Docker образ
├── railway.json         # Конфигурация Railway
├── .env.example         # Шаблон переменных окружения
├── data/
│   ├── users.json       # База пользователей (игнорируется Git)
│   └── orders.log       # Лог заказов (игнорируется Git)
└── tools/               # Утилиты для администрирования
```

## API Endpoints

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/yougile/webhook` | Приём событий от YouGile (требует `X-Yougile-Secret`) |
| `GET` | `/health` | Проверка работоспособности |

## Безопасность

- 🔒 Секреты хранятся **только** в `.env` (не в Git)
- 🔐 Вебхуки проверяются через `X-Yougile-Secret` заголовок
- 📁 `data/` добавлен в `.gitignore`

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Начать работу с ботом |
| `/help` | Справка по командам |
| `/users` | Список пользователей (только админ) |

## Лицензия

MIT
