from dotenv import load_dotenv
import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.vpn_clients import Subscription



from sqlalchemy import delete

delete_router = Router()
load_dotenv()



ADM = os.getenv('ADMIN_ID')


@delete_router.message(Command("deleteDB"))
async def delete_db(message: Message):
    text = message.text.replace("/deleteDB", "").strip()
    if message.from_user.id != int(ADM):
        return

    await message.answer(f"Использование: /deleteDB {text}")

    server_name = text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(Subscription)
            .where(Subscription.server_name == server_name)
        )

        await session.commit()

        await message.answer(
            f"Удалено записей: {result.rowcount}"
        )