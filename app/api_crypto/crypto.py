import asyncio
import os
from dotenv import load_dotenv
from aiosend import TESTNET, CryptoPay
from datetime import timedelta, datetime
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.payment import Payment
from app.db.models.vpn_clients import Subscription
from app.bot.inline_menu.main_menu import main_menu
from app.apiux.servers import SERVERS
from app.apiux.new_client import XUI

TOKEN=os.getenv('CRYPTO_TOKEN')
cp = CryptoPay(TOKEN)


async def create_invoice(amount: int, user_id: int):
    invoice = await cp.create_invoice(
        amount=amount,
        asset="USDT",
        description="Оплата доступа",
        payload=str(user_id)
    )

    return {
        "pay_url": invoice.bot_invoice_url,
        "invoice_id": invoice.invoice_id
    }

async def check_invoice_status(invoice_id):
    invoices = await cp.get_invoices(
        invoice_ids=[invoice_id]
    )

    if not invoices:
        return None

    invoice = invoices[0]

    return {
        "status": invoice.status,
        "invoice_id": invoice.invoice_id,
        "paid_asset": getattr(invoice, "paid_asset", None),
        "paid_amount": getattr(invoice, "paid_amount", None),
    }

    
async def monitor_payment(user_id: int, invoice_id: int, days: int, msg_id: int = None, bot=None):
    for _ in range(16): 
        
        try:
            
            result = await check_invoice_status(invoice_id)
            now = datetime.utcnow()
        
            if result and result["status"] == "paid":
                
                async with AsyncSessionLocal() as session:
                    result_payment = await session.execute(select(Payment).where(Payment.payment_id == invoice_id))
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
                        try:
                            await bot.delete_message(chat_id=user_id, message_id=msg_id)
                        except:
                            pass

                    await bot.send_message(chat_id=user_id, text=f"Оплата прошла успешно! Доступ продлён на {days} дней",
                                        reply_markup=main_menu)
                    
                    await bot.send_message(chat_id=os.getenv('ADMIN_ID'), text=f"Пользователь {user_id} оплатил доступ на {days} дней")
                

            elif result and result["status"] == "expired":
                await bot.send_message(chat_id=user_id, text="Оплата не прошла! Попробуйте позже", reply_markup=main_menu)
                return

        except Exception as e:
            print("WEBHOOK ERROR:", repr(e))
            await bot.send_message(chat_id=user_id,
                                text="Проверьте доступ!\n\nЕсли возники трудности свяжитесь с техподдержкой - @rsfromen.",
                                reply_markup=main_menu)
            await bot.send_message(chat_id=os.getenv('ADMIN_ID'), text=f"Ошибка при обработке платежа: {repr(e)}")
            return
            
    await asyncio.sleep(8)
    

    print("Invoice expired")
