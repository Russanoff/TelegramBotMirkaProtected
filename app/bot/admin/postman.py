import os
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Message
from dotenv import load_dotenv
from sqlalchemy import func, select

from app.bot.inline_menu.main_menu import main_menu
from app.db.database import AsyncSessionLocal
from app.db.models.user import User

load_dotenv()
postman_router = Router()

MAX_LEN = 4000  # лимит Telegram 4096


@postman_router.message(Command("postman"))
async def postman_command(message: Message, state: FSMContext):
    """Рассылка всем. Раньше уходила сразу, теперь - предпросмотр и подтверждение
    (отправляет та же кнопка «Отправить», что и в админ-меню)."""
    text = message.text.replace("/postman", "", 1).strip()

    if message.from_user.id not in [int(os.getenv("ADMIN_ID"))]:
        await message.answer("У вас нет доступа к этому функционалу.", reply_markup=main_menu)
        return

    if not text:
        await message.answer("Пожалуйста, введите текст для постмана.", reply_markup=main_menu)
        return

    if len(text) > MAX_LEN:
        await message.answer(f"Текст слишком длинный: {len(text)} из {MAX_LEN} символов.")
        return

    async with AsyncSessionLocal() as session:
        count = (await session.execute(select(func.count(User.id)))).scalar()

    await state.update_data(text=text, started=time.time())
    await message.answer(
        f"Получат: {count} пользователей (все, кто есть в базе).\n\nТекст:\n\n{text[:1500]}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Отправить", callback_data="adm:bc_send"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="adm:bc_cancel"),
        ]]),
        link_preview_options=LinkPreviewOptions(is_disabled=True))
