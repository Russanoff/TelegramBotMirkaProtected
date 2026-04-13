from aiogram import Router, F
from aiogram.filters.callback_data import CallbackQuery
from app.bot.inline_menu.main_menu import main_menu
from app.bot.inline_menu.config_menu import config_menu
from app.bot.texts.config_vpn import instruction
from datetime import timedelta, datetime
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.user import User


config_callbacks = Router()


@config_callbacks.callback_query(F.data == 'vpn_instruction')
async def have_app_next(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text(text=f'{instruction}\n\n🥇Чат ПроВПН - полная инструкция\n\nhttps://t.me/+3U-AMqBqDnpmZGJi',
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

        if user.ends_at and user.ends_at > now:
            end_date = user.ends_at.strftime("%d.%m.%Y %H:%M")
            await callback.message.edit_text(f"🟢Активные локации: 5\n👥Пользователей: {count}n\n\nПодписка активна✅🚀\nИстекает - {end_date}\n\n",
                                 reply_markup=main_menu)
        elif user.ends_at and user.ends_at < now:
            await callback.message.edit_text(f"🟢Активные локации: 5\n👥Пользователей: {count}n\n\nПодписка иcnекла🔴⏳", reply_markup=main_menu)
        elif not user.ends_at:
            await callback.message.edit_text(f"🟢Активные локации: 5\n👥Пользователей: {count}n\n\nНет подписки⏳", reply_markup=main_menu)
