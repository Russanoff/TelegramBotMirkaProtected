import logging
import os
import traceback

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ErrorEvent

from app.bot.admin.notify import notify_admin_throttled

logger = logging.getLogger(__name__)

errors_router = Router()

# Эти исключения - не поломка бота: пользователь заблокировал бота, нажал устаревшую кнопку и т.п.
_BENIGN_BAD_REQUEST = ("message is not modified", "query is too old", "message to edit not found",
                       "message can't be edited")


def _describe_update(update) -> tuple[str, object | None]:
    """(что делал пользователь, объект пользователя)."""
    if update.callback_query:
        cq = update.callback_query
        return f"кнопка «{cq.data}»", cq.from_user
    if update.message:
        m = update.message
        text = (m.text or "").strip()
        what = f"команда «{text.split()[0]}»" if text.startswith("/") else "сообщение"
        return what, m.from_user
    return "другое событие", None


def _where(exc: BaseException) -> str:
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return "неизвестно"
    last = frames[-1]
    return f"{os.path.basename(last.filename)}:{last.lineno} в {last.name}"


@errors_router.errors()
async def on_error(event: ErrorEvent, bot: Bot):
    exc = event.exception
    logger.error("Ошибка в обработчике: %r", exc, exc_info=exc)

    if isinstance(exc, TelegramForbiddenError):
        return True
    if isinstance(exc, TelegramBadRequest) and any(s in str(exc).lower() for s in _BENIGN_BAD_REQUEST):
        return True

    what, user = _describe_update(event.update)

    # кнопка не должна молчать: скажем пользователю, что что-то пошло не так
    cq = event.update.callback_query
    if cq:
        try:
            await cq.answer("Что-то пошло не так. Мы уже знаем об ошибке, попробуйте чуть позже.", show_alert=True)
        except Exception:
            pass

    who = f"{user.id} (@{user.username})" if user and user.username else (str(user.id) if user else "неизвестен")
    where = _where(exc)
    text = (f"🚨 Ошибка в боте\n"
            f"{type(exc).__name__}: {str(exc)[:200]}\n"
            f"Где: {where}\n"
            f"Действие: {what}\n"
            f"Пользователь: {who}")
    await notify_admin_throttled(f"err:{type(exc).__name__}:{where}", text, bot=bot)
    return True
