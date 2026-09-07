import secrets

from aiogram import Router
from aiogram.types import Message, InputMediaPhoto
from aiogram.filters import CommandStart, CommandObject
from app.bot.inline_menu.start_menu import keyboard_start
from app.bot.texts.hello import hello_text
from app.bot.inline_menu.main_menu import main_menu

from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from datetime import timedelta, datetime


router = Router()


@router.message(CommandStart())
async def start_func(message: Message, command: CommandObject):
    tg_id = message.from_user.id
    ref_payload = command.args

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        result_count = await session.execute(select(func.count(User.id)))
        count = result_count.scalar()
        user = result.scalar_one_or_none()
        now = datetime.utcnow()

        if user is None:
            referrer_id = None
            if ref_payload:
                try:
                    candidate_id = int(ref_payload)
                except ValueError:
                    candidate_id = None
                if candidate_id and candidate_id != tg_id:
                    ref_result = await session.execute(select(User).where(User.tg_id == candidate_id))
                    if ref_result.scalar_one_or_none():
                        referrer_id = candidate_id

            token = secrets.token_urlsafe(16)
            user = User(tg_id=tg_id, token=token, referrer_id=referrer_id)
            session.add(user)
            await session.commit()

        if not user.accepted_terms:
            await message.answer(F"Привет, {message.from_user.first_name}\n\n"
                                 F"{hello_text}", reply_markup=keyboard_start)
            return
        else:
            if user.ends_at and user.ends_at > now:
                end_date = user.ends_at.strftime("%d.%m.%Y %H:%M")
                await message.answer(f"🟢Активные локации: 6\n👥Пользователей: {count}\n\nПодписка активна✅🚀\nИстекает - {end_date}\n\n", reply_markup=main_menu)
            elif user.ends_at and user.ends_at < now:
                await message.answer(f"🟢Активные локации: 6\n👥Пользователей: {count}\n\nn\nПодписка иcnекла🔴⏳", reply_markup=main_menu)
            elif not user.ends_at:
                await message.answer(f"🟢Активные локации: 6\n👥Пользователей: {count}\n\n\n\nНет подписки⏳", reply_markup=main_menu)
