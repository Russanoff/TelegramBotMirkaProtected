import asyncio
import logging
from sqlalchemy import select

from app.bot.inline_menu.main_menu import main_menu
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
import datetime
from datetime import timedelta, datetime, date

logger = logging.getLogger(__name__)

REMINDER_TEXTS = {
    3: (
        "⚠️Через 3 дня истекает подписка!\n\n"
        "Не забудьте продлить доступ заранее, чтобы не остаться без VPN."
    ),
    1: (
        "⚠️Завтра истекает подписка!\n\n"
        "Если нет доступа к TG добавте эти временные прокси\n\n"
        "Сервер - `ltv.mirkaprotected.ru`\n"
        "Порт - `8080`\nЛогин - `john`\nПароль - `carter`\n\n"
        "Сервер - `usa.mirkaprotected.ru`\n"
        "Порт - `8010`\nЛогин - `piter`\nПароль - `parker`"
    ),
}


async def search_dates(session, days_ahead: int):
    today = date.today()
    target_day = today + timedelta(days=days_ahead)
    start = datetime.combine(target_day, datetime.min.time())
    end = datetime.combine(target_day, datetime.max.time())
    result = await session.execute(
        select(User).where(User.ends_at.between(start, end)))
    users = result.scalars().all()
    logger.info("Проверили базу на истекающие через %s дн.: найдено %s пользователей", days_ahead, len(users))
    return users


async def send_reminder(bot, session, days_ahead: int):
    users = await search_dates(session, days_ahead)
    text = REMINDER_TEXTS[days_ahead]

    for user in users:
        try:
            await bot.send_message(chat_id=user.tg_id, text=text,
                                   parse_mode='Markdown', reply_markup=main_menu)
        except Exception:
            logger.exception("Не удалось отправить напоминание пользователю %s", user.tg_id)


async def checker_bot(bot):
    while True:
        async with AsyncSessionLocal() as session:
            await send_reminder(bot, session, days_ahead=3)
        async with AsyncSessionLocal() as session:
            await send_reminder(bot, session, days_ahead=1)
        await asyncio.sleep(86400)
