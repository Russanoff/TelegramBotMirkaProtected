from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.vpn_clients import Subscription
from app.apiux.servers import SERVERS
from app.apiux.new_client import XUI

REFERRAL_BONUS_DAYS = 7


async def grant_referral_bonus(session: AsyncSession, user: User, bot=None) -> None:
    """Начисляет рефереру бонусные дни за первую успешную оплату приглашённого.

    Вызывать внутри уже открытой сессии payment-флоу, до session.commit().
    Начисление одноразовое (флаг referral_bonus_granted на приглашённом),
    чтобы повторные оплаты одного и того же пользователя не давали бонус снова.
    """
    if not user.referrer_id or user.referral_bonus_granted:
        return

    result = await session.execute(select(User).where(User.tg_id == user.referrer_id))
    referrer = result.scalar_one_or_none()
    if not referrer:
        return

    now = datetime.utcnow()
    if referrer.ends_at and referrer.ends_at > now:
        referrer.ends_at = referrer.ends_at + timedelta(days=REFERRAL_BONUS_DAYS)
    else:
        referrer.ends_at = now + timedelta(days=REFERRAL_BONUS_DAYS)

    user.referral_bonus_granted = True

    subs_res = await session.execute(select(Subscription).where(Subscription.user_id == referrer.tg_id))
    for sub in subs_res.scalars().all():
        try:
            server = SERVERS[sub.server_name]
            xui = XUI(server)
            await xui.login()
            await xui.update_expiry(client_name=f"TG_{referrer.tg_id}", ends_at=referrer.ends_at, subs_id=sub.sub_id)
            await xui.close()
        except Exception as e:
            print("REFERRAL XUI UPDATE ERROR:", repr(e))

    if bot:
        try:
            await bot.send_message(
                chat_id=referrer.tg_id,
                text=f"🎁 Ваш приглашённый друг оплатил подписку!\nВам начислено {REFERRAL_BONUS_DAYS} дней доступа.",
            )
        except Exception:
            pass
