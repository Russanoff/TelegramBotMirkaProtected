import os
from dotenv import load_dotenv
from aiosend import TESTNET, CryptoPay

TOKEN=os.getenv('CRYPTO_TOKEN')
cp = CryptoPay(TOKEN)


async def create_test_invoice(amount: int):
    invoice = await cp.create_invoice(
        amount=amount,
        asset="USDT",
        description="Оплата доступа"
    )

    return invoice.bot_invoice_url

