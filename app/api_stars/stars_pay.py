import logging
import os
from datetime import datetime

from aiogram import Router, F
from aiogram.filters.callback_data import CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, PreCheckoutQuery

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.payment import Payment
from app.bot.inline_menu.main_menu import main_menu
from app.bot.access import extend_user_access

logger = logging.getLogger(__name__)

stars_router = Router()

# Цены в Stars ⭐ — грубое приближение "1 Star ≈ 1 рубль" (взял те же числа, что в
# рублёвых тарифах в end_subs_menu.py/pay_callbacks.py). Курс Stars к валютам плавает
# и точного официального пересчёта нет, так что если цифры не устраивают —
# правь этот словарь И подписи кнопок в step_two_stars (app/bot/inline_menu/end_subs_menu.py),
# они специально не связаны кодом, чтобы не тащить импорт оплаты в модуль клавиатур.
STARS_TARIFFS = {
    10: 29,
    30: 99,
    60: 199,
    90: 299,
    365: 999,
}

back_to_stars_tariffs = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅ Назад", callback_data="stars_pay")]
])


@stars_router.callback_query(F.data.endswith('_accessstars'))
async def accessstars_day(callback: CallbackQuery):
    days = int(callback.data.split('_')[0])
    amount = STARS_TARIFFS.get(days)
    if amount is None:
        await callback.answer('Такой тариф не найден', show_alert=True)
        return

    await callback.answer('Формирую счёт в Stars...')
    await callback.message.edit_text(
        f"Оплата доступа на {days} дней — {amount}⭐\n\nСчёт придёт следующим сообщением",
        reply_markup=back_to_stars_tariffs,
    )

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Доступ на {days} дней",
        description="Продление доступа к MirkaProtected VPN",
        payload=f"stars:{days}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{days} дней", amount=amount)],
    )


@stars_router.pre_checkout_query()
async def stars_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Telegram требует ответ в течение 10 секунд, иначе платёж отменяется.
    # Тут проверять особо нечего (тариф уже проверен при формировании счёта),
    # поэтому всегда подтверждаем.
    await pre_checkout_query.answer(ok=True)


@stars_router.message(F.successful_payment)
async def stars_successful_payment(message: Message):
    payment_info = message.successful_payment
    user_id = message.from_user.id
    now = datetime.utcnow()

    try:
        days = int(payment_info.invoice_payload.split(':')[1])
    except (IndexError, ValueError):
        logger.error("Не смог разобрать payload оплаты Stars: %r", payment_info.invoice_payload)
        await message.answer(
            "Оплата прошла, но не получилось автоматически определить срок. "
            "Напишите в поддержку — @rsfromen."
        )
        await message.bot.send_message(
            chat_id=os.getenv('ADMIN_ID'),
            text=f"Stars: не разобрал payload у пользователя {user_id}: {payment_info.invoice_payload!r}"
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            result_user = await session.execute(select(User).where(User.tg_id == user_id))
            user = result_user.scalar_one_or_none()

            if not user:
                logger.error("Оплата Stars от неизвестного пользователя %s", user_id)
                await message.bot.send_message(
                    chat_id=os.getenv('ADMIN_ID'),
                    text=f"Stars: оплата от неизвестного пользователя {user_id}, доступ не выдан автоматически"
                )
                return

            pay_data = Payment(
                user_id=user_id,
                amount=payment_info.total_amount,
                days=days,
                currency='XTR',
                provider='TelegramStars',
                status='succeeded',
                payment_id=payment_info.telegram_payment_charge_id,
                create_payment=now,
            )
            session.add(pay_data)

            await extend_user_access(session, user, days, bot=message.bot)
            await session.commit()

        await message.answer(f"Оплата прошла успешно! Доступ продлён на {days} дней", reply_markup=main_menu)
        await message.bot.send_message(
            chat_id=os.getenv('ADMIN_ID'),
            text=f"Пользователь {user_id} оплатил доступ на {days} дней через Telegram Stars"
        )

    except Exception as e:
        logger.exception("Ошибка при выдаче доступа после оплаты Stars у %s", user_id)
        await message.answer(
            "Оплата прошла, но при выдаче доступа произошла ошибка. "
            "Напишите в поддержку — @rsfromen, разберёмся вручную.",
            reply_markup=main_menu,
        )
        await message.bot.send_message(
            chat_id=os.getenv('ADMIN_ID'),
            text=f"Ошибка при выдаче доступа после оплаты Stars у {user_id}: {repr(e)}"
        )
