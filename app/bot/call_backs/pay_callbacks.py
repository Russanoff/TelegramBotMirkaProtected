from aiogram import Router, F
from aiogram.filters.callback_data import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.api_yookassa.pay_requests import create_pay
from app.api_crypto.crypto import create_test_invoice
import uuid

from datetime import datetime

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.payment import Payment

pay_call = Router()

TARIFFS = {
    10: 50,
    30: 150,
    45: 200,
    60: 260,
    90: 350
}

CRYPTO_DAYS = {
    10: 1,
    30: 3,
    60: 6,
    90: 8
}


@pay_call.callback_query(F.data.endswith('_access'))
async def access_days(callback: CallbackQuery):
    days = int(callback.data.split('_')[0])
    amount = TARIFFS.get(days)
    print(f"Сумма платежа - {amount}")
    user_id = callback.from_user.id
    msg_id = callback.message.message_id
    now = datetime.utcnow()

    payment_url, payment_id = create_pay(amount, user_id, msg_id, days)

    async with AsyncSessionLocal() as session:
        result_payment = await session.execute(select(Payment).where(Payment.user_id == None))
        pay_data = Payment(
            user_id=user_id,
            amount=amount,
            days=days,
            currency='RUB',
            provider='YooKassaApi',
            status='pending',
            payment_id=payment_id,
            create_payment=now
        )

        session.add(pay_data)
        await session.commit()

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='💳 Оплатить', url=payment_url))
    builder.add(InlineKeyboardButton(text="⬅ Назад", callback_data="Extend"))

    await callback.message.edit_text(
        f"Оплата доступа на {days} дней\n\nК оплате — {amount} руб\n\nПоcле оплаты в этот чат будет отправлен статус платежа",
        reply_markup=builder.as_markup()
    )
    await callback.answer('Помним о замедлении TG и ожидаем...')
    
    
    

@pay_call.callback_query(F.data.endswith('_accesscry'))
async def accesscry_day(callback: CallbackQuery):
    days = int(callback.data.split('_')[0])
    user_id = callback.from_user.id
    payment_id = str(uuid.uuid4())
    amount = CRYPTO_DAYS.get(days)
    url = await create_test_invoice(amount=amount)
    now = datetime.utcnow()
    
    async with AsyncSessionLocal() as session:
        result_payment = await session.execute(select(Payment).where(Payment.user_id == None))
        pay_data = Payment(
            user_id=user_id,
            amount=amount,
            days=days,
            currency='USD',
            provider='CryptoPay',
            status='pending',
            payment_id=payment_id,
            create_payment=now
        )

        session.add(pay_data)
        await session.commit()
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='💳 Оплатить', url=url))
    builder.add(InlineKeyboardButton(text="⬅ Назад", callback_data="Extend"))
    
    await callback.message.edit_text(f"Оплата доступа на {days} дней\n\nК оплате - {amount} USD", reply_markup=builder.as_markup())
    await callback.answer('Помним о замедлении TG и ожидаем...')