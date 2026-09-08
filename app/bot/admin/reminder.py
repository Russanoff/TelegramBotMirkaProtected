import asyncio
import logging
from sqlalchemy import select

from app.bot.inline_menu.main_menu import main_menu
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
import datetime
from datetime import timedelta, datetime, date

logger = logging.getLogger(__name__)


async def search_dates(session):
    today = date.today()
    target_day = today + timedelta(days=1)
    start = datetime.combine(target_day, datetime.min.time())
    end = datetime.combine(target_day, datetime.max.time())
    result = await session.execute(
        select(User).where(User.ends_at.between(start, end)))
    users = result.scalars().all()
    logger.info("Проверили базу на просроченные: найдено %s пользователей", len(users))
    return users


async def send_reminder(bot, session):
    users = await search_dates(session)

    for user in users:
        try:
            await bot.send_message(chat_id=user.tg_id,
                                   text="⚠️Завтра истекает подписка!\n\n"
                                   "Если нет доступа к TG добавте эти временные прокси\n\n"
                                   "Сервер - `ltv.mirkaprotected.ru`\n"
                                   "Порт - `8080`\nЛогин - `john`\nПароль - `carter`\n\n"
                                   "Сервер - `usa.mirkaprotected.ru`\n"
                                   "Порт - `8010`\nЛогин - `piter`\nПароль - `parker`",
                                   parse_mode='Markdown', reply_markup=main_menu)
        except Exception:
            logger.exception("Не удалось отправить напоминание пользователю %s", user.tg_id)



async def checker_bot(bot):
    while True:
        async with AsyncSessionLocal() as session:
            await send_reminder(bot, session)
        await asyncio.sleep(86400)
