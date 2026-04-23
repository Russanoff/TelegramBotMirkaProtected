import json

from fastapi import FastAPI
from fastapi import Request

from app.apiux import servers
from app.bot.inline_menu.main_menu import main_menu
from app.db.models.vpn_clients import Subscription
from main import bot

from datetime import timedelta, datetime

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.payment import Payment
from app.apiux.new_client import XUI
from app.apiux.servers import SERVERS

app = FastAPI()


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

                if user.ends_at and user.ends_at > now:
                    user.ends_at = user.ends_at + timedelta(days=days)
                else:
                    user.ends_at = now + timedelta(days=days)

                if payment.status == "succeeded":
                    return {"ok": True}
                payment.status = 'succeeded'

                subs_res = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
                subs_for_id = subs_res.scalars()
                subs = subs_res.scalars().all()

                for sub in subs:
                    server = SERVERS[sub.server_name]
                    sub_id = sub.sub_id
                    xui = XUI(server)
                    await xui.login()
                    await xui.update_expiry(client_name=f"TG_{user_id}", ends_at=user.ends_at, subs_id=sub_id)
                    await xui.close()
                await session.commit()

                if msg_id:
                    await bot.delete_message(chat_id=user_id, message_id=msg_id)
                await bot.send_message(chat_id=user_id, text=f"Оплата прошла успешно! Доступ продлён на {days} дней",
                                       reply_markup=main_menu)

        else:
            await bot.send_message(chat_id=user_id, text="Оплата не прошла! Попробуйте позже", reply_markup=main_menu)

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        await bot.send_message(chat_id=user_id,
<<<<<<< HEAD
                               text="Проверьте доступ!\n\nЕсли возники трудности свяжитесь с техподдержкой - @rsfromen.",
                               reply_markup=main_menu)

    return {"ok": True}



@app.post('/crypto_bot/check_pay')
async def check_payment_crypto(request: Request):
    body = await request.body()
    
    print(body)
    return {"ok": True}
    
=======
                               text="Оплата не прошла! Технические проблемы. Повторите попытку оплаты через несколько минут.",
                               reply_markup=main_menu)

    return {"ok": True}
>>>>>>> 62d265c4750a7abcd0d8926a140034bda1470364
