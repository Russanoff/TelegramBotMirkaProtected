import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Message)
from dotenv import load_dotenv
from sqlalchemy import select

from app.bot.inline_menu.main_menu import main_menu
from app.db.database import AsyncSessionLocal
from app.db.models.user import User

load_dotenv()
logger = logging.getLogger(__name__)

winback_router = Router()

SITE_URL = "https://trial.mirkaprotected.ru/"
WINBACK_AFTER_DAYS = 7   # подписка истекла не меньше N дней назад
SEND_PAUSE = 0.1         # сек между сообщениями (лимит Telegram - 30 в секунду)

# Ссылка в первой строке: её видно в превью уведомления, даже если сам Telegram не открывается
WINBACK_TEXT = (
    f"Нет доступа к Telegram? Бесплатный VPN на 48 часов: {SITE_URL}\n\n"
    "Включите его, зайдите в бота и продлите подписку: оплата картой, криптой и Stars работает там."
)

_confirm_menu = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="Отправить", callback_data="winback_send"),
    InlineKeyboardButton(text="Отмена", callback_data="winback_cancel"),
]])

_send_lock = asyncio.Lock()


def _is_admin(user_id: int) -> bool:
    admin = os.getenv("ADMIN_ID")
    return bool(admin) and user_id == int(admin)


async def find_winback_users(session, now: datetime | None = None) -> list[User]:
    """Были с подпиской, она истекла давно, сообщение ещё не отправлялось."""
    now = now or datetime.utcnow()
    result = await session.execute(
        select(User).where(
            User.accepted_terms == True,  # noqa: E712
            User.ends_at.is_not(None),
            User.ends_at < now - timedelta(days=WINBACK_AFTER_DAYS),
            User.last_winback_at.is_(None),
        ))
    return list(result.scalars().all())


async def run_winback(bot) -> tuple[int, int, int]:
    """Отправляет сообщение. Возвращает (отправлено, заблокировали бота, ошибок)."""
    sent = blocked = failed = 0
    async with _send_lock:  # двойное нажатие кнопки не должно отправить всё дважды
        async with AsyncSessionLocal() as session:
            users = await find_winback_users(session)
            for user in users:
                try:
                    await bot.send_message(chat_id=user.tg_id, text=WINBACK_TEXT, reply_markup=main_menu)
                    sent += 1
                    user.last_winback_at = datetime.utcnow()
                except TelegramForbiddenError:
                    # заблокировал бота: помечаем, чтобы не пытаться снова
                    blocked += 1
                    user.last_winback_at = datetime.utcnow()
                except Exception:
                    # временная ошибка: не помечаем, попадёт в следующий запуск
                    failed += 1
                    logger.exception("Winback: не удалось отправить пользователю %s", user.tg_id)
                await session.commit()
                await asyncio.sleep(SEND_PAUSE)
    return sent, blocked, failed


@winback_router.message(Command("winback"))
async def winback_preview(message: Message):
    if not _is_admin(message.from_user.id):
        return
    async with AsyncSessionLocal() as session:
        users = await find_winback_users(session)
    if not users:
        await message.answer("Подходящих пользователей нет: либо подписки истекли недавно, "
                             "либо сообщение уже отправлялось.")
        return
    await message.answer(
        f"Получат сообщение: {len(users)} (подписка истекла больше {WINBACK_AFTER_DAYS} дней назад, "
        f"раньше не отправлялось).\n\nТекст:\n\n{WINBACK_TEXT}",
        reply_markup=_confirm_menu,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@winback_router.callback_query(F.data == "winback_send")
async def winback_send(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer("Отправляю...")
    await callback.message.edit_reply_markup(reply_markup=None)
    sent, blocked, failed = await run_winback(callback.bot)
    await callback.message.answer(
        f"📢 Отправлено: {sent}\n🚫 Заблокировали бота: {blocked}\n❌ Ошибок (повторятся при следующем запуске): {failed}")


@winback_router.callback_query(F.data == "winback_cancel")
async def winback_cancel(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer("Отменено")
    await callback.message.edit_reply_markup(reply_markup=None)
