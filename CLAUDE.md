# CLAUDE.md — MirkaProtected

Инструкции для Claude по работе с этим репозиторием. Отвечать владельцу по-русски.

## Что это
Telegram-бот @mirkaprotecbot: продаёт и выдаёт подписки на VPN (VLESS + Reality + gRPC) на нескольких узлах с панелями 3x-ui.
Оплата: ЮKassa (СБП/карты, вебхук), CryptoBot (aiosend), Telegram Stars. Есть рефералка, напоминания, сверка платежей, админ-меню `/admin`, лендинг бесплатного триала.

Стек: Python 3.12, aiogram 3, FastAPI + uvicorn, SQLAlchemy async + SQLite (`database.db`), httpx.

## Структура
- `main.py` — точка входа бота (polling), подключает роутеры и фоновые задачи (напоминания, сверка платежей).
- `app/api_yookassa/fastapi_conn.py` — FastAPI-приложение (`api.service`): вебхук ЮKassa, `/subs/<токен>`, триал.
- `app/api_main/` — эндпоинты подписок, триала, профиль маршрутизации.
- `app/apiux/` — работа с панелями 3x-ui: `servers.py` (список узлов `SERVERS`), `new_client.py` (клиент XUI), `reality_fix.py` (`/fixnode`, `/fixsni`), `vision.py`, `node_status.py`.
- `app/api_crypto/`, `app/api_stars/` — CryptoBot и Stars.
- `app/bot/` — хендлеры, колбэки, меню, тексты; `app/bot/admin/` — админ-функции.
- `app/db/` — модели (User, Payment, Subscription/vpn_clients, WebTrial) и инициализация БД.
- `app/web/` — лендинг триала.
- `tools/node_e2e_probe.py` — сквозная проверка узлов настоящим клиентом Xray.
- `docs/RUNBOOK.md` — **эксплуатация: деплой, откат, диагностика, добавление узла. Читать перед любыми действиями на серверах.**

Только на Маке владельца (в git не попадают, `notes/` в `.gitignore`):
- `notes/PROJECT_LOG.md` — журнал работы, состояние прода, открытые вопросы. Читать в начале сессии, если папка доступна.
- `notes/tests/` — наборы проверок на заглушках: `bash notes/tests/run_all.sh [v7 v12 ...]` (использует `venv/bin/python`).

## Правила
1. **Секреты.** Репозиторий публичный. Никогда не коммитить `.env`, `database.db`, `backups/`, `notes/`, токены, пароли, ключи. Значения из `.env` не выводить в чат и в логи. Пароли и ключи (ЮKassa, панели, root) меняет только владелец.
2. **Ветки.** Работа в ветке `feature/...` / `fix/...` / `chore/...`, затем слияние в `main`. Перед слиянием — тесты зелёные.
3. **Боевые системы** (сервер бота, панели 3x-ui, рассылки клиентам) — только с явного «да» владельца в текущем разговоре. Перед записью в панель — бэкап (так делает `reality_fix.py`); перед выкаткой — копия БД в `/root/backups/` (см. RUNBOOK §4).
4. **Выкатка и откат** — строго по `docs/RUNBOOK.md`. Перед SSH проверить, что VPN на Маке не гонит трафик через тормозящий узел (RUNBOOK §4, шаг 0).
5. Сервер бота слабый (1 ГБ RAM, без swap): тяжёлое там не запускать.
6. Узлы добавляются через `SERVERS` в `app/apiux/servers.py` (RUNBOOK §7); переносить клиентов не нужно.
7. Выводы о работе узлов проверять, а не предполагать (TCP из РФ через check-host, сквозной тест Xray); отличать «узел недоступен» от «режется протокол».

## Как запускать локально
```
python -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env   # если нет — попросить владельца; значения не придумывать
venv/bin/python main.py                                   # бот
venv/bin/uvicorn app.api_yookassa.fastapi_conn:app --port 8000   # API
```
