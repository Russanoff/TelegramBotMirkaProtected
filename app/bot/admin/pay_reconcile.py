"""Сверка зависших платежей ЮKassa.

ЮKassa шлёт вебхук только о части событий: об отмене (клиент не подтвердил платёж в банке)
бот не узнавал, платёж навсегда оставался pending, а клиент не получал «оплата не прошла».
Раз в несколько минут спрашиваем у ЮKassa реальный статус платежей, которые висят в pending.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select
from yookassa import Payment as YooKassaPayment

import app.api_yookassa.pay_requests  # noqa: F401  (настраивает ключи ЮKassa при импорте)
from app.bot.access import extend_user_access
from app.bot.admin.notify import notify_admin, notify_admin_throttled
from app.bot.inline_menu.main_menu import main_menu
from app.db.database import AsyncSessionLocal
from app.db.models.payment import Payment
from app.db.models.user import User

logger = logging.getLogger(__name__)

RECONCILE_EVERY = 300           # сек между проходами
MIN_AGE = timedelta(minutes=10)  # свежие не трогаем: вебхук приходит за секунды
MAX_AGE = timedelta(days=3)      # совсем старые уже не интересны
NOTIFY_USER_IF_NEWER_THAN = timedelta(hours=24)  # про давние отмены клиенту не пишем

_CANCEL_REASONS = {
    "expired_on_confirmation": "время на подтверждение платежа в банке истекло",
    "expired_on_capture": "платёж не был завершён вовремя",
    "canceled_by_merchant": "платёж отменён",
}


async def _tell_user(bot, tg_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id=tg_id, text=text, reply_markup=main_menu)
    except TelegramForbiddenError:
        pass
    except Exception:
        logger.exception("Сверка платежей: не удалось написать пользователю %s", tg_id)


async def _handle_canceled(bot, payment_id: int, reason: str | None) -> None:
    async with AsyncSessionLocal() as session:
        payment = (await session.execute(select(Payment).where(Payment.id == payment_id))).scalar_one()
        if payment.status != "pending":
            return
        payment.status = "canceled"
        await session.commit()
        user_id, amount, days, created = payment.user_id, payment.amount, payment.days, payment.create_payment

    why = _CANCEL_REASONS.get(reason or "", reason or "платёж отменён")
    await notify_admin(f"ℹ️ Платёж #{payment_id} не оплачен: {why}\n"
                       f"{amount} ₽ за {days} дн., клиент {user_id}, создан {created:%d.%m %H:%M} UTC", bot=bot)
    if datetime.utcnow() - created < NOTIFY_USER_IF_NEWER_THAN:
        await _tell_user(bot, user_id,
                         f"Оплата не прошла: {why}.\nДоступ не продлён, деньги не списаны. "
                         "Попробуйте ещё раз через «Продлить доступ».")


async def _handle_succeeded(bot, payment_id: int) -> None:
    """Деньги получены, а вебхук не дошёл: делаем то же, что делает вебхук."""
    async with AsyncSessionLocal() as session:
        payment = (await session.execute(select(Payment).where(Payment.id == payment_id))).scalar_one()
        if payment.status == "succeeded":
            return
        user = (await session.execute(select(User).where(User.tg_id == payment.user_id))).scalar_one_or_none()
        if user is None:
            await notify_admin(f"🚨 Платёж #{payment_id} оплачен в ЮKassa, но клиента {payment.user_id} нет в базе. Разберитесь вручную.", bot=bot)
            return
        payment.status = "succeeded"
        await extend_user_access(session, user, payment.days, bot=bot)
        await session.commit()
        user_id, amount, days = payment.user_id, payment.amount, payment.days

    await _tell_user(bot, user_id, f"Оплата прошла успешно! Доступ продлён на {days} дней")
    await notify_admin(f"⚠️ Платёж #{payment_id} ({amount} ₽, {days} дн., клиент {user_id}) был оплачен, но вебхук ЮKassa "
                       "не дошёл. Доступ продлён сверкой.", bot=bot)


async def reconcile_once(bot) -> dict:
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Payment.id, Payment.payment_id).where(
            Payment.provider == "YooKassaApi",
            Payment.status == "pending",
            Payment.create_payment < now - MIN_AGE,
            Payment.create_payment > now - MAX_AGE))
        pending = result.all()

    stats = {"checked": len(pending), "canceled": 0, "succeeded": 0, "still_pending": 0, "errors": 0}
    for payment_id, yk_id in pending:
        # каждый платёж изолирован: сбой одного (ЮKassa не ответила, строка пропала, БД занята)
        # не должен останавливать обработку остальных, включая оплаченный с потерянным вебхуком
        try:
            real = await asyncio.to_thread(YooKassaPayment.find_one, yk_id)
            if real.status == "canceled":
                cd = getattr(real, "cancellation_details", None)
                await _handle_canceled(bot, payment_id, getattr(cd, "reason", None) if cd else None)
                stats["canceled"] += 1
            elif real.status == "succeeded":
                await _handle_succeeded(bot, payment_id)
                stats["succeeded"] += 1
            else:
                stats["still_pending"] += 1
        except Exception as e:
            stats["errors"] += 1
            logger.exception("Сверка платежей: не удалось обработать платёж #%s", payment_id)
            await notify_admin_throttled(f"reconcile:{payment_id}",
                                         f"🚨 Сверка: не удалось обработать платёж #{payment_id}: {type(e).__name__}: {str(e)[:150]}",
                                         bot=bot, window=3600)
    return stats


async def payment_reconciler(bot) -> None:
    await asyncio.sleep(30)  # дать боту запуститься
    while True:
        try:
            await reconcile_once(bot)
        except Exception as e:
            logger.exception("Сверка платежей упала")
            await notify_admin_throttled("reconcile", f"🚨 Сверка платежей упала: {type(e).__name__}: {str(e)[:200]}", bot=bot, window=3600)
        await asyncio.sleep(RECONCILE_EVERY)
