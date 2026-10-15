from app.bot.safe_edit import safe_edit_text
from aiogram import Router, F
from aiogram.filters.callback_data import CallbackQuery
from app.bot.inline_menu.main_menu import main_menu
from app.bot.texts.main_menu import main_menu_text
from app.bot.inline_menu.config_menu import config_menu
from app.bot.texts.config_vpn import instruction
from app.apiux.servers import SERVERS
from datetime import timedelta, datetime
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.user import User


config_callbacks = Router()


@config_callbacks.callback_query(F.data == 'vpn_instruction')
async def have_app_next(callback: CallbackQuery):
    await callback.answer('')
    await safe_edit_text(callback.message, text=f'{instruction}\n\n🥇Чат ПроВПН - полная инструкция\n\nhttps://t.me/+3U-AMqBqDnpmZGJi',
                                     parse_mode='Markdown',
                                     reply_markup=main_menu)


@config_callbacks.callback_query(F.data == 'back_main_menu')
async def back_to_main_menu(callback: CallbackQuery):
    await callback.answer('Главное меню')
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.tg_id == callback.from_user.id))
        result_count = await session.execute(select(func.count(User.id)))
        count = result_count.scalar()
        user = user_res.scalar_one_or_none()
        now = datetime.utcnow()

        text = main_menu_text(user, count, len(SERVERS), now)
    await safe_edit_text(callback.message, text, reply_markup=main_menu, parse_mode="HTML")
