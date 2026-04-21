from aiogram.filters.callback_data import CallbackQuery
from app.bot.texts.agreement import agreement
from aiogram import Router, F
from app.bot.inline_menu.main_menu import main_menu
from app.bot.inline_menu.start_menu import confirm_menu
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
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

    await callback.answer('Соглашение принято!')
    await callback.message.edit_text('Соглашение принято! Добро пожаловать в Главное меню MirkaProtected!\n\n', reply_markup=main_menu)