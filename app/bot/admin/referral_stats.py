import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func

from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.bot.referral import REFERRAL_BONUS_DAYS

referral_stats_router = Router()


@referral_stats_router.message(Command("refstats"))
async def referral_stats(message: Message):
    if message.from_user.id != int(os.getenv('ADMIN_ID')):
        return

    async with AsyncSessionLocal() as session:
        total_referred_result = await session.execute(
            select(func.count(User.id)).where(User.referrer_id.isnot(None))
        )
        total_referred = total_referred_result.scalar()

        total_paid_result = await session.execute(
            select(func.count(User.id)).where(User.referral_bonus_granted == True)
        )
        total_paid = total_paid_result.scalar()

        top_result = await session.execute(
            select(User.referrer_id, func.count(User.id).label('cnt'))
            .where(User.referrer_id.isnot(None), User.referral_bonus_granted == True)
            .group_by(User.referrer_id)
            .order_by(func.count(User.id).desc())
            .limit(10)
        )
        top_referrers = top_result.all()

    text = (
        f"📊 Реферальная статистика\n\n"
        f"Пришло по реферальным ссылкам: {total_referred}\n"
        f"Из них оплатили (начислен бонус рефереру): {total_paid}\n"
        f"Выдано бонусных дней рефереров: {total_paid * REFERRAL_BONUS_DAYS}\n"
    )

    if top_referrers:
        text += "\n🏆 Топ по оплатившим рефералам:\n"
        for i, (referrer_id, cnt) in enumerate(top_referrers, start=1):
            name = str(referrer_id)
            try:
                chat = await message.bot.get_chat(referrer_id)
                name = chat.first_name or name
            except Exception:
                pass
            text += f"{i}. {name} (id {referrer_id}) — {cnt}\n"

    await message.answer(text)
