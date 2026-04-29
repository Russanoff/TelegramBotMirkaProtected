from dotenv import load_dotenv
import os
import asyncio
from sqlalchemy import select

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.inline_menu.main_menu import main_menu
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
import datetime
from datetime import timedelta, datetime, date

load_dotenv()
postman_router = Router()

@postman_router.message(Command("postman"))
async def postman_command(message: Message):
    text = message.text.replace("/postman", "").strip()
    
    if message.from_user.id not in [int(os.getenv("ADMIN_ID"))]:
        await message.answer("У вас нет доступа к этому функционалу.", reply_markup=main_menu)
        return
    
    if not text:
        await message.answer("Пожалуйста, введите текст для постмана.", reply_markup=main_menu)
        return
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await message.bot.send_message(chat_id=user.tg_id, text=text)
                sent += 1
            except Exception as e:
                failed += 1
    
    await message.answer(f"📢 Отправлено: {sent}\n❌ Ошибок: {failed}")