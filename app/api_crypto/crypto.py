import asyncio
import os
from dotenv import load_dotenv
from aiosend import TESTNET, CryptoPay

TOKEN=os.getenv('CRYPTO_TOKEN')
cp = CryptoPay(TOKEN)


async def create_invoice(amount: int, user_id: int):
    invoice = await cp.create_invoice(
        amount=amount,
        asset="USDT",
        description="Оплата доступа"
    )

    return invoice.bot_invoice_url

async def check_invoice_status(invoice_id: int):
    invoices = await cp.get_invoices(
        invoice_ids=invoice_id
    )

    if not invoices.items:
        return None

    invoice = invoices.items[0]

    return {
        "status": invoice.status,
        "invoice_id": invoice.invoice_id,
        "paid_asset": getattr(invoice, "paid_asset", None),
        "paid_amount": getattr(invoice, "paid_amount", None),
    }
    

async def monitor_payment(user_id: int, invoice_id: int):
    for _ in range(16): 

        result = await check_invoice_status(invoice_id)

        if result and result["status"] == "paid":
            print(f"Оплата прошла: {user_id}")

        await asyncio.sleep(8)  

    print("Invoice expired")
