import secrets

from aiogram import Router
from aiogram.types import Message, InputMediaPhoto
from aiogram.filters import CommandStart, CommandObject
from app.bot.inline_menu.start_menu import keyboard_start
from app.bot.texts.hello import hello_text
from app.bot.inline_menu.main_menu import main_menu
from app.apiux.servers import SERVERS

from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.web_trial import WebTrial
from app.bot.texts.web_trial import web_trial_hint_text
from app.bot.admin.notify import notify_admin_background
from app.bot.inline_menu.end_subs_menu import step_one
from app.bot.texts.pay import PAY_MENU_TEXT
from datetime import timedelta, datetime


router = Router()


@router.message(CommandStart())
async def start_func(message: Message, command: CommandObject):
    tg_id = message.from_user.id
    ref_payload = command.args

    # Переход с лендинга: /start web_<token> - привязываем пробный доступ к Telegram-аккаунту
    web_token = None
    web_referrer = None
    web_bound = False
    web_trial_ends = None
    want_pay = False
    if ref_payload == "pay":  # ссылка из подписки в Happ: открыть выбор способа оплаты
        want_pay = True
        ref_payload = None
    if ref_payload and ref_payload.startswith("web_"):
        web_token = ref_payload[len("web_"):]
        ref_payload = None

    async with AsyncSessionLocal() as session:
        if web_token:
            trial = (await session.execute(
                select(WebTrial).where(WebTrial.token == web_token))).scalar_one_or_none()
            # Триал привязывается только к первому, кто его открыл: пересланный токен
            # не даёт ни второго реферера, ни чужого триала.
            if trial and trial.tg_id is None:
                trial.tg_id = tg_id
                web_referrer = trial.referrer_id
                web_bound = True
                web_trial_ends = trial.ends_at
                await session.commit()

        result = await session.execute(select(User).where(User.tg_id == tg_id))
        result_count = await session.execute(select(func.count(User.id)))
        count = result_count.scalar()
        user = result.scalar_one_or_none()
        now = datetime.utcnow()

        if user is None:
            referrer_id = None
            if web_referrer and web_referrer != tg_id:
                ref_result = await session.execute(select(User).where(User.tg_id == web_referrer))
                if ref_result.scalar_one_or_none():
                    referrer_id = web_referrer
            if ref_payload:
                try:
                    candidate_id = int(ref_payload)
                except ValueError:
                    candidate_id = None
                if candidate_id and candidate_id != tg_id:
                    ref_result = await session.execute(select(User).where(User.tg_id == candidate_id))
                    if ref_result.scalar_one_or_none():
                        referrer_id = candidate_id

            token = secrets.token_urlsafe(16)
            user = User(tg_id=tg_id, token=token, referrer_id=referrer_id)
            session.add(user)
            await session.commit()

            # уведомление админу о новом клиенте
            if web_bound:
                source = "с сайта (триал)" + (f", пригласил {referrer_id}" if referrer_id else "")
            elif referrer_id:
                source = f"по реферальной ссылке (пригласил {referrer_id})"
            else:
                source = "напрямую"
            fu = message.from_user
            notify_admin_background(
                f"🆕 Новый клиент\n"
                f"ID: {tg_id}\n"
                f"Имя: {fu.full_name}" + (f" (@{fu.username})" if fu.username else "") + "\n"
                f"Пришёл: {source}\n"
                f"Всего пользователей: {count + 1}", bot=message.bot)

        if not user.accepted_terms:
            await message.answer(F"Привет, {message.from_user.first_name}\n\n"
                                 F"{hello_text}", reply_markup=keyboard_start)
            return
        else:
            if want_pay:
                await message.answer(PAY_MENU_TEXT, reply_markup=step_one)
                return
            if user.ends_at and user.ends_at > now:
                end_date = user.ends_at.strftime("%d.%m.%Y %H:%M")
                await message.answer(f"🟢Активные локации: {len(SERVERS)}\n👥Пользователей: {count}\n\nПодписка активна✅🚀\nИстекает - {end_date}\n\n", reply_markup=main_menu)
            elif user.ends_at and user.ends_at < now:
                await message.answer(f"🟢Активные локации: {len(SERVERS)}\n👥Пользователей: {count}\n\nПодписка истекла🔴⏳", reply_markup=main_menu)
            elif not user.ends_at:
                await message.answer(f"🟢Активные локации: {len(SERVERS)}\n👥Пользователей: {count}\n\n\n\nНет подписки⏳", reply_markup=main_menu)

            # Условия уже приняты раньше, значит ссылка с сайта расширяется сразу
            if web_bound:
                hint = web_trial_hint_text(user, web_trial_ends, now, len(SERVERS))
                if hint:
                    await message.answer(hint)
