import json
import logging
import os
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi import Request

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

app = FastAPI()

app.include_router(subs_router)

@app.post('/yookassa/check_pay')
async def check_payment(request: Request):

    body = await request.body()
    data = json.loads(body)
    access = data.get('event')
    payment = data.get('object', {})
    metadata = payment.get('metadata', {})
    user_id = metadata.get("user_id")
    now = datetime.utcnow()
    msg_id = metadata.get("msg_id")
    days = int(metadata.get("term"))

    try:
        if access == "payment.succeeded":
            async with AsyncSessionLocal() as session:
                result_payment = await session.execute(select(Payment).where(Payment.payment_id == payment.get('id')))
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
            await bot.send_message(chat_id=user_id, text="Оплата не прошла! Попробуйте позже", reply_markup=main_menu)

    except Exception as e:
        logger.exception("Ошибка при обработке платежа ЮKassa у %s", user_id)
        await bot.send_message(chat_id=user_id,
                               text="Проверьте доступ!\n\nЕсли возники трудности свяжитесь с техподдержкой - @rsfromen.",
                               reply_markup=main_menu)
        await bot.send_message(chat_id=os.getenv('ADMIN_ID'), text=f"Ошибка при обработке платежа: {repr(e)}")

    return {"ok": True}



