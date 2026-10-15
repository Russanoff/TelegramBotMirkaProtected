"""Админ-меню: /admin. Всё, что раньше требовало помнить команды, - кнопками, с подтверждением для необратимого."""
import asyncio
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import BaseFilter, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (BotCommand, BotCommandScopeChat, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, LinkPreviewOptions, Message)
from sqlalchemy import delete, func, select

from app.apiux.node_status import all_nodes_status, node_status
from app.apiux.reality_fix import SNI_CANDIDATES
from app.apiux.servers import SERVERS
from app.bot.access import extend_user_access
from app.bot.admin import pay_reconcile
from app.bot.admin.fixnode import NodeActionError, build_fixnode_preview, build_fixsni_preview
from app.bot.admin.winback import build_winback_preview
from app.bot.inline_menu.main_menu import main_menu
from app.bot.referral import REFERRAL_BONUS_DAYS
from app.bot.safe_edit import safe_edit_text
from app.db.database import AsyncSessionLocal
from app.db.models.payment import Payment
from app.db.models.user import User
from app.db.models.vpn_clients import Subscription
from app.db.models.web_trial import WebTrial

logger = logging.getLogger(__name__)

PROCESS_STARTED = time.time()
REPO_DIR = Path(__file__).resolve().parents[3]
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
MANUAL_EXTEND_DAYS = (7, 30)
BROADCAST_PAUSE = 0.05  # сек между сообщениями (лимит Telegram - 30 в секунду)
_broadcast_lock = asyncio.Lock()

PROVIDERS = {"YooKassaApi": "ЮKassa", "CryptoPay": "CryptoBot", "TelegramStars": "Stars"}
STATUS_ICONS = {"succeeded": "✅", "pending": "⏳", "canceled": "❌"}


class AdminStates(StatesGroup):
    broadcast_text = State()
    find_user = State()


class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        admin = os.getenv("ADMIN_ID")
        user = getattr(event, "from_user", None)
        return bool(admin and user and user.id == int(admin))


admin_menu_router = Router()
admin_menu_router.message.filter(IsAdmin())
admin_menu_router.callback_query.filter(IsAdmin())


def _kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows])


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _back(target: str = "adm:home", label: str = "⬅️ Назад") -> InlineKeyboardMarkup:
    return _kb([_btn(label, target)])


async def _show(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    await callback.answer()
    await safe_edit_text(callback.message, text[:4000], reply_markup=markup, link_preview_options=NO_PREVIEW)


def _fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y %H:%M") if dt else "—"


def _sub_state(ends_at: datetime | None, now: datetime) -> str:
    if ends_at is None:
        return "нет подписки"
    if ends_at > now:
        return f"до {ends_at:%d.%m.%Y %H:%M} (ещё {(ends_at - now).days} дн.)"
    return f"истекла {ends_at:%d.%m.%Y}"


# ---------------------------------------------------------------- главное меню

def _home():
    return ("🛠 Админ-панель\n\nВыберите раздел.",
            _kb([_btn("📊 Статистика", "adm:stats"), _btn("💳 Платежи", "adm:pay")],
                [_btn("🌍 Узлы", "adm:nodes"), _btn("📣 Рассылки", "adm:mail")],
                [_btn("👥 Клиенты", "adm:cl"), _btn("🧹 Сервис", "adm:svc")]))


@admin_menu_router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    await state.clear()
    text, markup = _home()
    await message.answer(text, reply_markup=markup)


@admin_menu_router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено. Меню: /admin")


@admin_menu_router.callback_query(F.data == "adm:home")
async def home_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, markup = _home()
    await _show(callback, text, markup)


# ---------------------------------------------------------------- статистика

async def _money(session, since: datetime | None) -> str:
    q = select(Payment.provider, Payment.currency, func.count(Payment.id), func.sum(Payment.amount)).where(Payment.status == "succeeded")
    if since is not None:
        q = q.where(Payment.create_payment >= since)
    rows = (await session.execute(q.group_by(Payment.provider, Payment.currency))).all()
    if not rows:
        return "нет"
    return "; ".join(f"{PROVIDERS.get(p, p)} {s or 0} {c} ({n})" for p, c, n, s in rows)


async def stats_text() -> str:
    now = datetime.utcnow()
    today = datetime.combine(now.date(), datetime.min.time())
    async with AsyncSessionLocal() as s:
        count = lambda *where: s.execute(select(func.count(User.id)).where(*where))
        total = (await count()).scalar()
        accepted = (await count(User.accepted_terms == True)).scalar()  # noqa: E712
        active = (await count(User.ends_at > now)).scalar()
        expired = (await count(User.ends_at < now)).scalar()
        never = (await count(User.ends_at.is_(None))).scalar()
        referred = (await count(User.referrer_id.isnot(None))).scalar()
        ref_paid = (await count(User.referral_bonus_granted == True)).scalar()  # noqa: E712
        payers = (await s.execute(select(func.count(func.distinct(Payment.user_id))).where(Payment.status == "succeeded"))).scalar()
        pending = (await s.execute(select(func.count(Payment.id)).where(Payment.status == "pending"))).scalar()
        all_time = await _money(s, None)
        week = await _money(s, now - timedelta(days=7))
        day = await _money(s, today)
    return (f"📊 Статистика ({now:%d.%m.%Y %H:%M} UTC)\n\n"
            f"Пользователей: {total} (приняли условия: {accepted})\n"
            f"Подписка активна: {active} · истекла: {expired} · не было: {never}\n"
            f"Платили хотя бы раз: {payers}\n\n"
            f"Оплаты сегодня: {day}\n"
            f"За 7 дней: {week}\n"
            f"За всё время: {all_time}\n"
            f"Ожидают оплаты: {pending}\n\n"
            f"Рефералы: пришло {referred}, оплатили {ref_paid} (бонусных дней выдано: {ref_paid * REFERRAL_BONUS_DAYS})")


@admin_menu_router.callback_query(F.data == "adm:stats")
async def stats_callback(callback: CallbackQuery):
    await _show(callback, await stats_text(), _kb([_btn("🔄 Обновить", "adm:stats")], [_btn("⬅️ В меню", "adm:home")]))


# ---------------------------------------------------------------- платежи

async def payments_text() -> str:
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(Payment).order_by(Payment.id.desc()).limit(10))).scalars().all()
        pending = (await s.execute(select(func.count(Payment.id)).where(Payment.status == "pending"))).scalar()
    lines = [f"{STATUS_ICONS.get(p.status, '❔')} #{p.id} {p.create_payment:%d.%m %H:%M} {PROVIDERS.get(p.provider, p.provider)} "
             f"{p.amount} {p.currency} · {p.days} дн. · {p.status} · клиент {p.user_id}" for p in rows]
    return (f"💳 Последние платежи (время UTC), ожидают: {pending}\n\n" + ("\n".join(lines) or "Платежей пока нет") +
            "\n\n«Сверить» спрашивает ЮKassa о платежах, которые висят в ожидании (бот делает это сам раз в 5 минут).")


@admin_menu_router.callback_query(F.data == "adm:pay")
async def payments_callback(callback: CallbackQuery):
    await _show(callback, await payments_text(),
                _kb([_btn("🔄 Сверить с ЮKassa сейчас", "adm:pay_rec")], [_btn("⬅️ В меню", "adm:home")]))


@admin_menu_router.callback_query(F.data == "adm:pay_rec")
async def payments_reconcile_callback(callback: CallbackQuery):
    await callback.answer("Проверяю...")
    st = await pay_reconcile.reconcile_once(callback.bot)
    text = (f"Сверка завершена.\nПроверено: {st['checked']}\nОтменено: {st['canceled']}\n"
            f"Оплачено без вебхука (доступ продлён): {st['succeeded']}\nЕщё ждут оплаты: {st['still_pending']}\nОшибок: {st['errors']}")
    await safe_edit_text(callback.message, text, reply_markup=_kb([_btn("💳 К платежам", "adm:pay")], [_btn("⬅️ В меню", "adm:home")]))


# ---------------------------------------------------------------- узлы

def _node_icon(st: dict) -> str:
    if not st["ok"]:
        return "🔴"
    return "🟢" if st.get("xray_state") == "running" and st.get("enable") else "🟡"


def _node_line(st: dict) -> str:
    if not st["ok"]:
        return f"🔴 {st['name']} ({st['key']}): панель не отвечает ({st.get('error', '?')})"
    return (f"{_node_icon(st)} {st['name']} ({st['key']}): xray {st.get('xray_state')}, клиентов {st['clients']}, "
            f"онлайн {st['online'] if st['online'] is not None else '?'}\n     SNI {st['sni']}, uTLS {st['fingerprint']}")


async def _nodes_screen():
    statuses = await all_nodes_status()
    keys = [s["key"] for s in statuses]
    rows = [[_btn(f"{_node_icon(s)} {s['key']}", f"adm:node:{s['key']}") for s in statuses[i:i + 3]] for i in range(0, len(statuses), 3)]
    rows += [[_btn("🔄 Обновить", "adm:nodes")], [_btn("⬅️ В меню", "adm:home")]]
    text = "🌍 Узлы (онлайн - сколько клиентов подключено сейчас)\n\n" + "\n".join(_node_line(s) for s in statuses) + \
           "\n\nВыберите узел, чтобы перенастроить его или сменить SNI."
    return text, _kb(*rows)


@admin_menu_router.callback_query(F.data == "adm:nodes")
async def nodes_callback(callback: CallbackQuery):
    await callback.answer("Опрашиваю узлы...")
    text, markup = await _nodes_screen()
    await safe_edit_text(callback.message, text, reply_markup=markup)


def _valid_key(key: str) -> bool:
    return key in SERVERS


@admin_menu_router.callback_query(F.data.startswith("adm:node:"))
async def node_card_callback(callback: CallbackQuery):
    key = callback.data.split(":")[2]
    if not _valid_key(key):
        await callback.answer("Неизвестный узел")
        return
    await callback.answer("Читаю узел...")
    st = await node_status(key)
    if st["ok"]:
        text = (f"{_node_icon(st)} {st['name']} ({key})\n\n"
                f"xray: {st.get('xray_state')} {st.get('xray_version') or ''} {('ошибка: ' + st['xray_error']) if st['xray_error'] else ''}\n"
                f"Inbound включён: {'да' if st['enable'] else 'НЕТ'}\n"
                f"Клиентов: {st['clients']}, онлайн сейчас: {st['online'] if st['online'] is not None else '?'}\n"
                f"SNI: {st['sni']}\nuTLS: {st['fingerprint']}\nService Name: {st['service_name'] or '(пусто)'}\n"
                f"Сервер работает без перезагрузки: {st['uptime_days']} дн.")
    else:
        text = f"🔴 {st['name']} ({key})\n\nПанель не отвечает: {st.get('error', '?')}\nПерестроить узел нельзя, пока панель недоступна."
    rows = []
    if st["ok"]:
        rows += [[_btn("🔁 Перенастроить конфиги", f"adm:rot:{key}")],
                 [_btn("🌐 Сменить SNI (подобрать)", f"adm:sni:{key}"), _btn("📋 SNI из списка", f"adm:snilist:{key}")]]
    rows += [[_btn("🔄 Обновить", f"adm:node:{key}"), _btn("⬅️ К узлам", "adm:nodes")]]
    await safe_edit_text(callback.message, text, reply_markup=_kb(*rows))


async def _preview(callback: CallbackQuery, builder, *args):
    await callback.answer("Готовлю предпросмотр...")
    try:
        text, markup = await builder(*args)
    except NodeActionError as e:
        text, markup = str(e), _back("adm:nodes", "⬅️ К узлам")
    await safe_edit_text(callback.message, text, reply_markup=markup)


@admin_menu_router.callback_query(F.data.startswith("adm:rot:"))
async def rotate_callback(callback: CallbackQuery):
    key = callback.data.split(":")[2]
    if not _valid_key(key):
        await callback.answer("Неизвестный узел")
        return
    await _preview(callback, build_fixnode_preview, key, None)


@admin_menu_router.callback_query(F.data.startswith("adm:sni:"))
async def sni_auto_callback(callback: CallbackQuery):
    key = callback.data.split(":")[2]
    if not _valid_key(key):
        await callback.answer("Неизвестный узел")
        return
    await _preview(callback, build_fixsni_preview, key, "auto")


@admin_menu_router.callback_query(F.data.startswith("adm:snilist:"))
async def sni_list_callback(callback: CallbackQuery):
    key = callback.data.split(":")[2]
    if not _valid_key(key):
        await callback.answer("Неизвестный узел")
        return
    domains = list(SNI_CANDIDATES)
    rows = [[_btn(d, f"adm:snipick:{key}:{d}") for d in domains[i:i + 2]] for i in range(0, len(domains), 2)]
    rows.append([_btn("⬅️ К узлу", f"adm:node:{key}")])
    await _show(callback, f"📋 Выберите новый SNI для {SERVERS[key]['name']}.\nДомен будет проверен перед применением.", _kb(*rows))


@admin_menu_router.callback_query(F.data.startswith("adm:snipick:"))
async def sni_pick_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 4 or not _valid_key(parts[2]) or parts[3] not in SNI_CANDIDATES:
        await callback.answer("Неизвестный узел или домен")
        return
    await _preview(callback, build_fixsni_preview, parts[2], parts[3])


# ---------------------------------------------------------------- рассылки

@admin_menu_router.callback_query(F.data == "adm:mail")
async def mail_callback(callback: CallbackQuery):
    await _show(callback, "📣 Рассылки",
                _kb([_btn("↩️ Вернуть ушедших (подписка истекла)", "adm:winback")],
                    [_btn("📢 Сообщение всем пользователям", "adm:bc")],
                    [_btn("⬅️ В меню", "adm:home")]))


@admin_menu_router.callback_query(F.data == "adm:winback")
async def winback_menu_callback(callback: CallbackQuery):
    text, markup = await build_winback_preview()
    await _show(callback, text, markup or _back("adm:mail", "⬅️ К рассылкам"))


@admin_menu_router.callback_query(F.data == "adm:bc")
async def broadcast_start_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.broadcast_text)
    await _show(callback, "📢 Пришлите текст рассылки одним сообщением. Его получат все пользователи бота.\n"
                          "Перед отправкой я покажу, сколько человек получат, и попрошу подтвердить.\nОтмена: /cancel",
                _back("adm:mail", "❌ Отмена"))


@admin_menu_router.message(StateFilter(AdminStates.broadcast_text), F.text)
async def broadcast_text_received(message: Message, state: FSMContext):
    text = message.text
    if text.startswith("/"):
        await message.answer("Пришлите обычный текст (не команду). Отмена: /cancel")
        return
    async with AsyncSessionLocal() as s:
        count = (await s.execute(select(func.count(User.id)))).scalar()
    await state.update_data(text=text)
    await message.answer(f"Получат: {count} пользователей (все, кто есть в базе).\n\nТекст:\n\n{text[:1500]}",
                         reply_markup=_kb([_btn("✅ Отправить", "adm:bc_send"), _btn("❌ Отмена", "adm:bc_cancel")]),
                         link_preview_options=NO_PREVIEW)


@admin_menu_router.callback_query(F.data == "adm:bc_cancel")
async def broadcast_cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _show(callback, "Рассылка отменена.", _back("adm:mail", "⬅️ К рассылкам"))


async def run_broadcast(bot, text: str) -> tuple[int, int, int]:
    sent = blocked = failed = 0
    async with _broadcast_lock:  # двойное нажатие не должно отправить всё дважды
        async with AsyncSessionLocal() as s:
            ids = [i for (i,) in (await s.execute(select(User.tg_id))).all()]
        for tg_id in ids:
            try:
                await bot.send_message(chat_id=tg_id, text=text)
                sent += 1
            except TelegramForbiddenError:
                blocked += 1
            except Exception:
                failed += 1
                logger.exception("Рассылка: не удалось отправить %s", tg_id)
            await asyncio.sleep(BROADCAST_PAUSE)
    return sent, blocked, failed


@admin_menu_router.callback_query(F.data == "adm:bc_send")
async def broadcast_send_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")
    await state.clear()
    if not text:
        await _show(callback, "Текст рассылки потерян (бот перезапускался?). Начните заново.", _back("adm:mail", "⬅️ К рассылкам"))
        return
    await callback.answer("Отправляю...")
    await callback.message.edit_reply_markup(reply_markup=None)
    sent, blocked, failed = await run_broadcast(callback.bot, text)
    await callback.message.answer(f"📢 Рассылка завершена\nОтправлено: {sent}\nЗаблокировали бота: {blocked}\nОшибок: {failed}",
                                  reply_markup=_back("adm:home", "🛠 В меню"))


# ---------------------------------------------------------------- клиенты

@admin_menu_router.callback_query(F.data == "adm:cl")
async def clients_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _show(callback, "👥 Клиенты",
                _kb([_btn("🆕 Последние регистрации", "adm:cl_recent")], [_btn("🔎 Найти по Telegram ID", "adm:cl_find")],
                    [_btn("⬅️ В меню", "adm:home")]))


@admin_menu_router.callback_query(F.data == "adm:cl_recent")
async def clients_recent_callback(callback: CallbackQuery):
    now = datetime.utcnow()
    async with AsyncSessionLocal() as s:
        users = (await s.execute(select(User).order_by(User.id.desc()).limit(10))).scalars().all()
    lines = [f"{'✓' if u.accepted_terms else '✗'} {u.tg_id} · {_sub_state(u.ends_at, now)}" for u in users]
    rows = [[_btn(str(u.tg_id), f"adm:cl_card:{u.tg_id}") for u in users[i:i + 2]] for i in range(0, len(users), 2)]
    rows.append([_btn("⬅️ К клиентам", "adm:cl")])
    await _show(callback, "🆕 Последние 10 регистраций (✓ - приняли условия). Нажмите ID, чтобы открыть карточку.\n\n" + "\n".join(lines), _kb(*rows))


@admin_menu_router.callback_query(F.data == "adm:cl_find")
async def clients_find_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.find_user)
    await _show(callback, "🔎 Пришлите Telegram ID клиента (число). Отмена: /cancel", _back("adm:cl", "❌ Отмена"))


async def client_card(tg_id: int):
    now = datetime.utcnow()
    async with AsyncSessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()
        if user is None:
            return None
        pays = (await s.execute(select(Payment).where(Payment.user_id == tg_id).order_by(Payment.id.desc()).limit(3))).scalars().all()
        servers = [n for (n,) in (await s.execute(select(Subscription.server_name).where(Subscription.user_id == tg_id))).all()]
        web = (await s.execute(select(func.count(WebTrial.id)).where(WebTrial.tg_id == tg_id))).scalar()
    pay_lines = "\n".join(f"  {STATUS_ICONS.get(p.status, '❔')} #{p.id} {p.create_payment:%d.%m %H:%M} {p.amount} {p.currency} {p.days} дн. {p.status}" for p in pays) or "  нет"
    text = (f"👤 Клиент {tg_id}\n\n"
            f"Условия приняты: {'да' if user.accepted_terms else 'нет'} · пробный период: {'был' if user.trial_used else 'нет'}\n"
            f"Подписка: {_sub_state(user.ends_at, now)}\n"
            f"Приглашён: {user.referrer_id or '—'}\n"
            f"Серверы с выданными клиентами: {', '.join(servers) if servers else 'нет'}\n"
            f"Триалов с сайта привязано: {web}\n"
            f"Последние платежи:\n{pay_lines}")
    markup = _kb([_btn(f"➕ {d} дн.", f"adm:cl_ext:{tg_id}:{d}") for d in MANUAL_EXTEND_DAYS], [_btn("⬅️ К клиентам", "adm:cl")])
    return text, markup


@admin_menu_router.callback_query(F.data.startswith("adm:cl_card:"))
async def client_card_callback(callback: CallbackQuery):
    tg_id = callback.data.split(":")[2]
    card = await client_card(int(tg_id)) if tg_id.isdigit() else None
    if card is None:
        await _show(callback, "Клиент не найден.", _back("adm:cl", "⬅️ К клиентам"))
        return
    await _show(callback, *card)


@admin_menu_router.message(StateFilter(AdminStates.find_user), F.text)
async def client_find_received(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer("Нужен числовой Telegram ID. Отмена: /cancel")
        return
    await state.clear()
    card = await client_card(int(raw))
    if card is None:
        await message.answer("Клиент не найден.", reply_markup=_back("adm:cl", "⬅️ К клиентам"))
        return
    await message.answer(card[0], reply_markup=card[1])


def _parse_extend(data: str):
    parts = data.split(":")
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit() or int(parts[3]) not in MANUAL_EXTEND_DAYS:
        return None
    return int(parts[2]), int(parts[3])


@admin_menu_router.callback_query(F.data.startswith("adm:cl_ext:"))
async def extend_confirm_callback(callback: CallbackQuery):
    parsed = _parse_extend(callback.data)
    if not parsed:
        await callback.answer("Некорректные данные")
        return
    tg_id, days = parsed
    async with AsyncSessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()
    if user is None:
        await _show(callback, "Клиент не найден.", _back("adm:cl", "⬅️ К клиентам"))
        return
    now = datetime.utcnow()
    new_end = (user.ends_at if user.ends_at and user.ends_at > now else now) + timedelta(days=days)
    await _show(callback,
                f"Продлить клиенту {tg_id} доступ на {days} дн.?\nНовый срок: {new_end:%d.%m.%Y %H:%M} UTC.\n"
                "Срок обновится на панелях. Реферальный бонус не начисляется. Клиенту придёт уведомление.",
                _kb([_btn("✅ Подтвердить", f"adm:cl_extok:{tg_id}:{days}"), _btn("❌ Отмена", f"adm:cl_card:{tg_id}")]))


@admin_menu_router.callback_query(F.data.startswith("adm:cl_extok:"))
async def extend_do_callback(callback: CallbackQuery):
    parsed = _parse_extend(callback.data)
    if not parsed:
        await callback.answer("Некорректные данные")
        return
    tg_id, days = parsed
    await callback.answer("Продлеваю...")
    async with AsyncSessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()
        if user is None:
            await safe_edit_text(callback.message, "Клиент не найден.", reply_markup=_back("adm:cl", "⬅️ К клиентам"))
            return
        await extend_user_access(s, user, days, bot=callback.bot, grant_bonus=False)
        await s.commit()
        new_end = user.ends_at
    try:
        await callback.bot.send_message(chat_id=tg_id, text=f"Администратор продлил ваш доступ на {days} дн. Он действует до {new_end:%d.%m.%Y %H:%M}.",
                                        reply_markup=main_menu)
        notified = "клиенту написали"
    except Exception:
        notified = "клиенту написать не удалось (возможно, заблокировал бота)"
    await safe_edit_text(callback.message, f"✅ Доступ клиента {tg_id} продлён на {days} дн. до {new_end:%d.%m.%Y %H:%M} UTC, {notified}.",
                         reply_markup=_kb([_btn("👤 К карточке", f"adm:cl_card:{tg_id}")], [_btn("⬅️ В меню", "adm:home")]))


# ---------------------------------------------------------------- сервис

@admin_menu_router.callback_query(F.data == "adm:svc")
async def service_callback(callback: CallbackQuery):
    await _show(callback, "🧹 Сервис",
                _kb([_btn("🗑 Записи про удалённые узлы", "adm:svc_orph")], [_btn("ℹ️ О боте", "adm:about")], [_btn("⬅️ В меню", "adm:home")]))


async def _orphans() -> list[tuple[str, int]]:
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(Subscription.server_name, func.count(Subscription.id)).group_by(Subscription.server_name))).all()
    return [(name, n) for name, n in rows if name not in SERVERS]


@admin_menu_router.callback_query(F.data == "adm:svc_orph")
async def orphans_callback(callback: CallbackQuery):
    orphans = await _orphans()
    if not orphans:
        await _show(callback, "Записей про удалённые узлы нет, чистить нечего.", _back("adm:svc", "⬅️ В сервис"))
        return
    rows = [[_btn(f"Удалить {name} ({n})", f"adm:svc_del:{name}")] for name, n in orphans] + [[_btn("⬅️ В сервис", "adm:svc")]]
    await _show(callback, "В базе остались записи о клиентах на узлах, которых больше нет в конфигурации. "
                          "В работе они не мешают. Удаление необратимо, но касается только этих записей.", _kb(*rows))


@admin_menu_router.callback_query(F.data.startswith("adm:svc_del:"))
async def orphans_confirm_callback(callback: CallbackQuery):
    name = callback.data.split(":", 2)[2]
    if name in SERVERS or name not in dict(await _orphans()):
        await callback.answer("Такой записи нет или узел ещё действует")
        return
    n = dict(await _orphans())[name]
    await _show(callback, f"Удалить {n} записей про узел {name}?",
                _kb([_btn("✅ Удалить", f"adm:svc_delok:{name}"), _btn("❌ Отмена", "adm:svc_orph")]))


@admin_menu_router.callback_query(F.data.startswith("adm:svc_delok:"))
async def orphans_delete_callback(callback: CallbackQuery):
    name = callback.data.split(":", 2)[2]
    if name in SERVERS:  # узел действующий - ни при каких условиях не трогаем
        await callback.answer("Узел действует, не удаляю")
        return
    async with AsyncSessionLocal() as s:
        res = await s.execute(delete(Subscription).where(Subscription.server_name == name))
        await s.commit()
    await _show(callback, f"Удалено записей про узел {name}: {res.rowcount}", _back("adm:svc", "⬅️ В сервис"))


def _git_version() -> str:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h %s (%cd)", "--date=format:%d.%m %H:%M"], cwd=REPO_DIR,
                             capture_output=True, text=True, timeout=3)
        return out.stdout.strip() or "неизвестно"
    except Exception:
        return "неизвестно"


@admin_menu_router.callback_query(F.data == "adm:about")
async def about_callback(callback: CallbackQuery):
    version = await asyncio.to_thread(_git_version)
    up = timedelta(seconds=int(time.time() - PROCESS_STARTED))
    await _show(callback, f"ℹ️ О боте\n\nВерсия кода: {version}\nБот работает без перезапуска: {up}\n"
                          f"Узлов в конфигурации: {len(SERVERS)} ({', '.join(SERVERS)})",
                _kb([_btn("⬅️ В сервис", "adm:svc")], [_btn("🛠 В меню", "adm:home")]))


# ---------------------------------------------------------------- подсказки команд в Telegram

ADMIN_COMMANDS = [
    BotCommand(command="admin", description="🛠 Админ-меню"),
    BotCommand(command="winback", description="Вернуть ушедших клиентов"),
    BotCommand(command="fixnode", description="Перенастроить узел"),
    BotCommand(command="fixsni", description="Сменить SNI узла"),
    BotCommand(command="refstats", description="Реферальная статистика"),
    BotCommand(command="user_count", description="Число пользователей"),
]


async def setup_admin_commands(bot) -> None:
    """Список команд в меню «/» показывается только админу."""
    admin = os.getenv("ADMIN_ID")
    if not admin or not admin.isdigit():
        return
    try:
        await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=int(admin)))
    except Exception:
        logger.exception("Не удалось установить список команд для админа")
