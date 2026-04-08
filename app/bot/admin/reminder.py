import asyncio
from sqlalchemy import select

from app.bot.inline_menu.main_menu import main_menu
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
import datetime
from datetime import timedelta, datetime, date


async def search_dates(session):
    today = date.today()
    target_day = today + timedelta(days=1)
    start = datetime.combine(target_day, datetime.min.time())
    end = datetime.combine(target_day, datetime.max.time())
    result = await session.execute(
        select(User).where(User.ends_at.between(start, end)))
    users = result.scalars().all()
    print("Проверили базу на просроченные")
    return users


async def send_reminder(bot, session):
    users = await search_dates(session)

    try:
        for user in users:
            await bot.send_message(chat_id=user.tg_id, text="⚠️Подписка заканчивается!", reply_markup=main_menu)
    except Exception as e:
        print(f"Ошибка: {e}")



async def checker_bot(bot):
    while True:
        async with AsyncSessionLocal() as session:
            await send_reminder(bot, session)
        await asyncio.sleep(86400)
