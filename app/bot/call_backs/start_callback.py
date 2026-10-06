from aiogram.filters.callback_data import CallbackQuery
from app.bot.texts.agreement import agreement
from aiogram import Router, F
from app.bot.inline_menu.main_menu import main_menu
from app.bot.inline_menu.start_menu import confirm_menu
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.web_trial import WebTrial
from app.apiux.servers import SERVERS
from app.bot.texts.web_trial import web_trial_hint_text
from datetime import datetime
from sqlalchemy import select


start_menu_callback = Router()


@start_menu_callback.callback_query(F.data == 'open_agreements')
async def open_agreements(callback: CallbackQuery):
    await callback.answer('Пользовательское соглашение')
    await callback.message.edit_text(f'{agreement}', reply_markup=confirm_menu)


@start_menu_callback.callback_query(F.data == 'confirm')
async def open_main_menu(callback: CallbackQuery):
    tg_user = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_user)
        )
        user = result.scalar_one()

        user.accepted_terms = True
        await session.commit()

        # Пришёл с сайта: подсказка зависит от того, жива ли его личная подписка
        trial_result = await session.execute(
            select(WebTrial.ends_at).where(WebTrial.tg_id == tg_user).order_by(WebTrial.id.desc()).limit(1))
        trial_ends = trial_result.scalar_one_or_none()
        hint = web_trial_hint_text(user, trial_ends, datetime.utcnow(), len(SERVERS)) if trial_ends else ""

    text = 'Соглашение принято! Добро пожаловать в Главное меню MirkaProtected!\n\n'
    if hint:
        text += hint

    await callback.answer('Соглашение принято!')
    await callback.message.edit_text(text, reply_markup=main_menu)