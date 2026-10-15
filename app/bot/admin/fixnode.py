import asyncio
import logging
import os
import secrets

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

from app.apiux.reality_fix import SNI_CANDIDATES, RotationError, rotate_reality
from app.apiux.servers import SERVERS

load_dotenv()
logger = logging.getLogger(__name__)

fixnode_router = Router()

_MAX_DOMAIN_LEN = 40  # callback_data в Telegram не длиннее 64 байт


def _is_admin(user_id: int) -> bool:
    admin = os.getenv("ADMIN_ID")
    return bool(admin) and user_id == int(admin)


def _nodes_list() -> str:
    return "\n".join(f"{k} - {v['name']}" for k, v in SERVERS.items())


def _buttons(apply_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Применить", callback_data=apply_data),
        InlineKeyboardButton(text="Отмена", callback_data="fixnode_cancel"),
    ]])


async def _read_nodes() -> dict:
    """{ключ: сводка} по всем узлам, только чтение; недоступные узлы пропускаются."""
    async def one(key):
        try:
            return key, await rotate_reality(key, apply=False)
        except Exception:
            return key, None
    return {k: v for k, v in await asyncio.gather(*(one(k) for k in SERVERS)) if v}


@fixnode_router.message(Command("fixnode"))
async def fixnode_preview(message: Message, command: CommandObject):
    if not _is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    key = parts[0].upper() if parts else ""
    domain = parts[1].lower() if len(parts) > 1 else None
    if key not in SERVERS:
        await message.answer(f"Укажите узел: /fixnode GE или /fixnode GE www.samsung.com (с новым SNI)\n\n{_nodes_list()}")
        return
    if domain and len(domain) > _MAX_DOMAIN_LEN:
        await message.answer("Слишком длинное имя домена.")
        return
    try:
        info = await rotate_reality(key, apply=False, sni=domain)
    except Exception as e:
        logger.exception("fixnode: не удалось прочитать узел %s", key)
        await message.answer(f"Не удалось подготовить узел {key}: {e}")
        return
    sni_line = (f"\nSNI: {info['old_sni']} -> {domain} (проверка: {info['sni_check']})" if domain else
                f"\nSNI останется {info['old_sni']} (чтобы сменить, укажите домен: /fixnode {key} www.samsung.com)")
    await message.answer(
        f"{info['name']}\n"
        f"Сейчас: uTLS {info['old_fingerprint']}, Service Name {info['old_service_name_len']} симв., "
        f"Short IDs {info['old_short_ids']}, клиентов {info['clients']}.{sni_line}\n\n"
        "Будет заменено: Service Name (вида Get_api_Service), uTLS (на другой), Short IDs, "
        "публичный и приватный ключи. "
        "Перед записью сохраню бэкап, после записи проверю, что клиенты на месте, иначе откачу.\n\n"
        "Подключённые клиенты отвалятся, пока не обновят подписку в приложении.",
        reply_markup=_buttons(f"fixnode_apply:{key}" + (f":{domain}" if domain else "")))


@fixnode_router.message(Command("fixsni"))
async def fixsni_preview(message: Message, command: CommandObject):
    """Меняет только SNI/dest узла. Ключи, Short IDs, Service Name и uTLS не трогает."""
    if not _is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if not parts:
        nodes = await _read_nodes()
        current = "\n".join(f"{k} - {v['name']}: {nodes[k]['old_sni'] if k in nodes else 'узел недоступен'}" for k, v in SERVERS.items())
        await message.answer(
            "Смена SNI на узле: /fixsni PL www.samsung.com или /fixsni PL auto (подберу домен, который не занят другими узлами).\n\n"
            f"Сейчас:\n{current}\n\n"
            "Проверенные кандидаты (TLS 1.3 + HTTP/2, открываются из РФ):\n" + ", ".join(SNI_CANDIDATES))
        return
    key = parts[0].upper()
    if key not in SERVERS:
        await message.answer(f"Неизвестный узел.\n\n{_nodes_list()}")
        return
    domain = parts[1].lower() if len(parts) > 1 else "auto"
    if domain != "auto" and len(domain) > _MAX_DOMAIN_LEN:
        await message.answer("Слишком длинное имя домена.")
        return
    info = None
    try:
        if domain == "auto":
            used = {v["old_sni"] for v in (await _read_nodes()).values()}
            pool = [d for d in SNI_CANDIDATES if d not in used] or list(SNI_CANDIDATES)
            secrets.SystemRandom().shuffle(pool)
            for candidate in pool[:8]:  # домен из списка мог временно не пройти проверку: берём следующий
                try:
                    info = await rotate_reality(key, apply=False, rotate=False, sni=candidate)
                    domain = candidate
                    break
                except RotationError:
                    continue
            if info is None:
                await message.answer("Не нашёл подходящий домен: ни один из проверенных кандидатов сейчас не прошёл проверку TLS.")
                return
        else:
            info = await rotate_reality(key, apply=False, rotate=False, sni=domain)
    except Exception as e:
        await message.answer(f"Не получилось: {e}")
        return
    await message.answer(
        f"{info['name']}\n"
        f"SNI: {info['old_sni']} -> {domain}\n"
        f"Проверка домена: {info['sni_check']}\n"
        f"Клиентов на узле: {info['clients']}\n\n"
        "Изменятся только SNI и dest. Ключи, Short IDs, Service Name и uTLS остаются прежними. "
        "Перед записью сохраню бэкап, после проверю клиентов, при расхождении откачу.\n\n"
        "Подключённые клиенты отвалятся, пока не обновят подписку (приложение делает это раз в час).",
        reply_markup=_buttons(f"fixsni_apply:{key}:{domain}"))


async def _apply_and_report(callback: CallbackQuery, key: str, rotate: bool, sni: str | None) -> None:
    await callback.answer("Применяю...")
    await callback.message.edit_reply_markup(reply_markup=None)
    try:
        r = await rotate_reality(key, apply=True, rotate=rotate, sni=sni)
    except RotationError as e:
        await callback.message.answer(f"❌ {key}: {e}. Ничего не изменено.")
        return
    except Exception as e:
        logger.exception("fixnode: ошибка при замене на узле %s", key)
        await callback.message.answer(f"❌ {key}: ошибка {type(e).__name__}. Проверьте панель вручную.")
        return
    if r.get("verified"):
        lines = [f"✅ {r['name']}: изменения применены, клиентов {r['clients']} на месте."]
        if rotate:
            lines += [f"uTLS: {r['old_fingerprint']} -> {r['new_fingerprint']}", f"Service Name: {r['new_service_name']}"]
        if sni:
            lines.append(f"SNI: {r['old_sni']} -> {r['new_sni']}")
        lines += [f"Бэкап: {r['backup']}", "", "Обновите подписку в приложении и проверьте пинг. "
                  "Не помогло: верните прежнее командой /fixsni " + f"{key} {r['old_sni']}"]
        await callback.message.answer("\n".join(lines))
    elif r.get("rolled_back"):
        await callback.message.answer(f"⚠️ {key}: проверка после записи не прошла, прежние настройки возвращены.")
    else:
        await callback.message.answer(
            f"🚨 {key}: проверка не прошла и откат не подтверждён. Откройте панель, бэкап: {r.get('backup')}")


@fixnode_router.callback_query(F.data.startswith("fixnode_apply:"))
async def fixnode_apply(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    parts = callback.data.split(":", 2)
    key = parts[1]
    domain = parts[2] if len(parts) > 2 else None
    if key not in SERVERS:
        await callback.answer("Неизвестный узел")
        return
    await _apply_and_report(callback, key, rotate=True, sni=domain)


@fixnode_router.callback_query(F.data.startswith("fixsni_apply:"))
async def fixsni_apply(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    parts = callback.data.split(":", 2)
    if len(parts) != 3 or parts[1] not in SERVERS:
        await callback.answer("Неизвестный узел")
        return
    await _apply_and_report(callback, parts[1], rotate=False, sni=parts[2])


@fixnode_router.callback_query(F.data == "fixnode_cancel")
async def fixnode_cancel(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer("Отменено")
    await callback.message.edit_reply_markup(reply_markup=None)
