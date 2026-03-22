from aiogram import Router
from aiogram.types import Message, InputMediaPhoto
from aiogram.filters import CommandStart
from app.bot.inline_menu.start_menu import keyboard_start
from app.bot.texts.hello import hello_text
from app.bot.inline_menu.main_menu import main_menu

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.vpn_clients import Subscription
from datetime import timedelta, datetime


router = Router()


@router.message(CommandStart())
async def start_func(message: Message):
    tg_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        now = datetime.utcnow()

        if user is None:
            user = User(tg_id=tg_id)
            session.add(user)
            await session.commit()

        if not user.accepted_terms:
            await message.answer(F"Привет, {message.from_user.first_name}\n\n"
                                 F"{hello_text}", reply_markup=keyboard_start)
            return
        else:
            if user.ends_at and user.ends_at > now:
                end_date = user.ends_at.strftime("%d.%m.%Y %H:%M")
                await message.answer(f"Главное меню\n\nПодписка активна✅🚀\nИстекает - {end_date}\n\n", reply_markup=main_menu)
            elif user.ends_at and user.ends_at < now:
                await message.answer(f"Главное меню\n\nПодписка иcnекла🔴⏳", reply_markup=main_menu)
            elif not user.ends_at:
                await message.answer(f"Главное меню\n\nНет подписки⏳", reply_markup=main_menu)

