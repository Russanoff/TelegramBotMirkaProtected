import json
import logging
import os
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi import Request

import yookassa
from yookassa import Payment as YooKassaPayment

from app.bot.inline_menu.main_menu import main_menu
from main import bot

from datetime import datetime

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.payment import Payment
from app.api_main.subs_endpoint import subs_router
from app.bot.access import extend_user_access

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

yookassa.Configuration.account_id = os.getenv("SHOP_ID")
yookassa.Configuration.secret_key = os.getenv("SECRET_KEY")

app = FastAPI()

app.include_router(subs_router)

@app.post('/yookassa/check_pay')
async def check_payment(request: Request):

    body = await request.body()
    data = json.loads(body)
    payment_payload = data.get('object', {})
    payment_id = payment_payload.get('id')
    metadata = payment_payload.get('metadata', {})
    user_id = metadata.get("user_id")
    now = datetime.utcnow()
    msg_id = metadata.get("msg_id")
    days = int(metadata.get("term"))

    # ЮKassa не подписывает вебхуки — тело запроса теоретически можно подделать
    # и получить доступ без оплаты. Поэтому не доверяем event/status из вебхука,
    # а переспрашиваем реальный статус платежа напрямую у ЮKassa по api-ключу.
    real_payment = YooKassaPayment.find_one(payment_id)

    try:
        if real_payment.status == "succeeded":
            async with AsyncSessionLocal() as session:
                result_payment = await session.execute(select(Payment).where(Payment.payment_id == payment_id))
                payment = result_payment.scalar_one_or_none()

                result_user = await session.execute(select(User).where(User.tg_id == user_id))
                user = result_user.scalar_one_or_none()

                if not user or not payment:
                    return {"ok": True}

                if payment.status == "succeeded":
                    return {"ok": True}
                payment.status = 'succeeded'

                await extend_user_access(session, user, days, bot=bot)
                await session.commit()

                if msg_id:
                    try:
                        await bot.delete_message(chat_id=user_id, message_id=msg_id)
                    except:
                        pass

                await bot.send_message(chat_id=user_id, text=f"Оплата прошла успешно! Доступ продлён на {days} дней",
                                       reply_markup=main_menu)
                await bot.send_message(chat_id=os.getenv('ADMIN_ID'), text=f"Пользователь {user_id} оплатил доступ на {days} дней")

        else:
            async with AsyncSessionLocal() as session:
                result_payment = await session.execute(select(Payment).where(Payment.payment_id == payment_id))
                payment = result_payment.scalar_one_or_none()
                if payment and payment.status == "pending":
                    payment.status = real_payment.status
                    await session.commit()

            await bot.send_message(chat_id=user_id, text="Оплата не прошла! Попробуйте позже", reply_markup=main_menu)

    except Exception as e:
        logger.exception("Ошибка при обработке платежа ЮKassa у %s", user_id)
        await bot.send_message(chat_id=user_id,
                               text="Проверьте доступ!\n\nЕсли возникли трудности свяжитесь с техподдержкой - @rsfromen.",
                               reply_markup=main_menu)
        await bot.send_message(chat_id=os.getenv('ADMIN_ID'), text=f"Ошибка при обработке платежа: {repr(e)}")

    return {"ok": True}



