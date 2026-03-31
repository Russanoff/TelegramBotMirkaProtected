from dotenv import load_dotenv
import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.user import User

load_dotenv()
router_admin = Router()


@router_admin.message(Command(commands=['user_count']))
async def user_count(msg: Message):

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(User.id)))
        result_accept = await session.execute(select(func.count(User.accepted_terms)))
        result_trial = await session.execute(select(func.count(User.trial_used)))
        trial = result_trial.scalar()
        accepted = result_accept.scalar()
        count = result.scalar()

    user = msg.from_user.id
    admin = int(os.getenv('ADMIN_ID'))
    if user != admin:
        return
    await msg.answer(f"Колличество пользователей: {count}\n"
                     f"Прошли соглашение: {accepted}\n"
                     f"Есть пробный: {trial}\n")
