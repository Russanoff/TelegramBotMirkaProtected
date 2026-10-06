import logging
import os

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

from app.apiux.reality_fix import RotationError, rotate_reality
from app.apiux.servers import SERVERS

load_dotenv()
logger = logging.getLogger(__name__)

fixnode_router = Router()


def _is_admin(user_id: int) -> bool:
    admin = os.getenv("ADMIN_ID")
    return bool(admin) and user_id == int(admin)


@fixnode_router.message(Command("fixnode"))
async def fixnode_preview(message: Message, command: CommandObject):
    if not _is_admin(message.from_user.id):
        return
    key = (command.args or "").strip().upper()
    if key not in SERVERS:
        nodes = "\n".join(f"{k} - {v['name']}" for k, v in SERVERS.items())
        await message.answer(f"Укажите узел: /fixnode GE\n\n{nodes}")
        return
    try:
        info = await rotate_reality(key, apply=False)
    except Exception as e:
        logger.exception("fixnode: не удалось прочитать узел %s", key)
        await message.answer(f"Не удалось прочитать узел {key}: {e}")
        return
    await message.answer(
        f"{info['name']}\n"
        f"Сейчас: uTLS {info['old_fingerprint']}, Service Name {info['old_service_name_len']} симв., "
        f"Short IDs {info['old_short_ids']}, клиентов {info['clients']}.\n\n"
        "Будет заменено: Service Name, uTLS (на другой), Short IDs, публичный и приватный ключи. "
        "Перед записью сохраню бэкап, после записи проверю, что клиенты на месте, иначе откачу.\n\n"
        "Подключённые клиенты отвалятся, пока не обновят подписку в приложении.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Применить", callback_data=f"fixnode_apply:{key}"),
            InlineKeyboardButton(text="Отмена", callback_data="fixnode_cancel"),
        ]]))


@fixnode_router.callback_query(F.data.startswith("fixnode_apply:"))
async def fixnode_apply(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    key = callback.data.split(":", 1)[1]
    if key not in SERVERS:
        await callback.answer("Неизвестный узел")
        return
    await callback.answer("Применяю...")
    await callback.message.edit_reply_markup(reply_markup=None)
    try:
        r = await rotate_reality(key, apply=True)
    except RotationError as e:
        await callback.message.answer(f"❌ {key}: {e}. Ничего не изменено.")
        return
    except Exception as e:
        logger.exception("fixnode: ошибка при замене на узле %s", key)
        await callback.message.answer(f"❌ {key}: ошибка {type(e).__name__}. Проверьте панель вручную.")
        return
    if r.get("verified"):
        await callback.message.answer(
            f"✅ {r['name']}: параметры заменены, клиентов {r['clients']} на месте.\n"
            f"uTLS: {r['old_fingerprint']} -> {r['new_fingerprint']}\n"
            f"Бэкап: {r['backup']}\n\nТеперь обновите подписку в приложении и проверьте пинг.")
    elif r.get("rolled_back"):
        await callback.message.answer(f"⚠️ {key}: проверка после записи не прошла, прежние настройки возвращены.")
    else:
        await callback.message.answer(
            f"🚨 {key}: проверка не прошла и откат не подтверждён. Откройте панель, бэкап: {r.get('backup')}")


@fixnode_router.callback_query(F.data == "fixnode_cancel")
async def fixnode_cancel(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer("Отменено")
    await callback.message.edit_reply_markup(reply_markup=None)
