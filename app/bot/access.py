import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.vpn_clients import Subscription
from app.apiux.servers import SERVERS
from app.apiux.new_client import XUI
from app.bot.referral import grant_referral_bonus

logger = logging.getLogger(__name__)


async def extend_user_access(session: AsyncSession, user: User, days: int, bot=None, grant_bonus: bool = True) -> None:
    """Продлевает user.ends_at на days, обновляет expiry на всех уже выданных
    VPN-клиентах и начисляет реферальный бонус пригласившему (если применимо).

    Общая точка для всех трёх способов оплаты (ЮKassa/CryptoPay/Stars) —
    раньше эта логика была продублирована в каждом из них по отдельности.
    Session не коммитится - это решает вызывающий код, после своих
    специфичных изменений (например payment.status).
    """
    now = datetime.utcnow()
    if user.ends_at and user.ends_at > now:
        user.ends_at = user.ends_at + timedelta(days=days)
    else:
        user.ends_at = now + timedelta(days=days)

    subs_res = await session.execute(select(Subscription).where(Subscription.user_id == user.tg_id))
    for sub in subs_res.scalars().all():
        if sub.server_name not in SERVERS:
            # узел удалён из конфигурации (запись в БД осталась): ходить некуда
            continue
        try:
            server = SERVERS[sub.server_name]
            xui = XUI(server)
            await xui.login()
            await xui.update_expiry(client_name=f"TG_{user.tg_id}", ends_at=user.ends_at, subs_id=sub.sub_id)
            if server.get("vision"):  # клиент во втором («боевом») входе: тот же срок
                await xui.update_expiry(client_name=f"TG_{user.tg_id}{server['vision']['suffix']}", ends_at=user.ends_at, subs_id=sub.sub_id)
            await xui.close()
        except Exception:
            logger.exception(
                "Не удалось обновить expiry на панели %s для пользователя %s",
                sub.server_name, user.tg_id,
            )

    if grant_bonus:  # ручное продление админом не считается оплатой приглашённого
        await grant_referral_bonus(session, user, bot=bot)
