from aiogram import Router, F
from aiogram.filters.callback_data import CallbackQuery
from app.bot.texts.config_vpn import instruction
from app.bot.inline_menu.config_menu import config_menu
from app.bot.inline_menu.main_menu import main_menu

from datetime import timedelta, datetime

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.payment import Payment
from app.db.models.vpn_clients import Subscription
from app.bot.inline_menu.end_subs_menu import step_one


main_menu_router = Router()


@main_menu_router.callback_query(F.data == 'proxy_anty')
async def proxy_anty(call: CallbackQuery):
    await call.answer(text="Пожалуйста, ожидайте...")
    tg_id = call.from_user.id
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        result_user = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result_user.scalar_one_or_none()

    if user and user.ends_at > now:
        await call.message.edit_text(text=f'🥇Чат Proxy для браузера  - полная инструкция\n\nhttps://t.me/+3U-AMqBqDnpmZGJi',
                                     parse_mode='Markdown', reply_markup=main_menu)
    else:
        pass


@main_menu_router.callback_query(F.data == 'config_vpn')
async def config_vpn(callback: CallbackQuery):
    await callback.answer('Настройка устройства')
    await callback.message.edit_text(f'{instruction}', reply_markup=config_menu)


@main_menu_router.callback_query(F.data == 'profile')
async def profile(callback: CallbackQuery):
    name = callback.from_user.first_name
    tg_id = callback.from_user.id
    await callback.answer('ожидайте...')

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        
        payment_result = await session.execute(select(Payment).where(Payment.user_id == tg_id))
        payment = payment_result.scalars().first()
        now = datetime.utcnow()

    if user.ends_at and user.ends_at > now:
        day_count = (user.ends_at - now).days
        end_date = user.ends_at.strftime("%d.%m.%Y %H:%M")
        await callback.message.edit_text(f'🖥{name}\nID: {tg_id}\n\n'
                                     f'Статус: ✅🚀 Активна до {end_date}\n\n\n'
                                     f'Последний платёж: {payment.amount} {payment.currency}\n'
                                     f'Совершён: {payment.create_payment.strftime("%d.%m.%Y %H:%M")}\n'
                                     f'Осталось: {day_count} дней', reply_markup=main_menu)
    elif user.ends_at and user.ends_at < now:
        end_date = user.ends_at.strftime("%d.%m.%Y %H:%M")
        await callback.message.edit_text(f'🖥{name}\nID: {tg_id}\n\n'
                                         f'Статус: 🔴⏳ Подписка истекла! {end_date}\n'
                                         f'Последний платёж: {payment.amount} {payment.currency}\n'
                                         f'Совершён: {payment.create_payment.strftime("%d.%m.%Y %H:%M")}\n', reply_markup=main_menu)
    elif not user.ends_at:
        await callback.message.edit_text(f'Профиль 🖥{name}\nID: {tg_id}\n\n'
                                         f'Статус: ⏳ Нет подписки', reply_markup=main_menu)


@main_menu_router.callback_query(F.data == "proxy_tg")
async def proxy_tg(call: CallbackQuery):
    await call.answer(text="Пожалуйста, ожидайте...")
    tg_id = call.from_user.id
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        result_user = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result_user.scalar_one_or_none()

    if user and user.ends_at > now:
        await call.message.edit_text(
            text=f'🥇Чат - @ProxyMTProto\n\nВ данном чате есть прокси для Telegram\nПодключать нужно несколько прокси сразу для лучшей работы мессенджера\n\n🥇Чат - @ProxyMTProto',
            parse_mode='Markdown', reply_markup=main_menu)
    else:
        pass


@main_menu_router.callback_query(F.data == "support")
async def support_answer(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(text="Если остались вопросы, возникли проблемы с подключением или обнаружили ошибку\n\nНапишите администратору - @rsfromen", reply_markup=main_menu)