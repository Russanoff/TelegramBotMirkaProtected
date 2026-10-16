import datetime
import json
import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from app.apiux import servers
from app.apiux import new_client
from app.db.models.user import User
from app.db.database import AsyncSessionLocal
from sqlalchemy import select
from app.apiux.new_client import XUI
from app.apiux.servers import SERVERS
from fastapi.responses import JSONResponse, PlainTextResponse
from app.apiux.new_client import XUI

import base64
import sys

from app.db.models.vpn_clients import Subscription
from app.bot.admin.notify import notify_admin_throttled

logger = logging.getLogger(__name__)

subs_router = APIRouter()

PROFILE_TITLE = "MirkaProtected"
BOT_URL = "https://t.me/mirkaprotecbot"
PAY_URL = BOT_URL + "?start=pay"   # открывает в боте выбор способа оплаты
ANNOUNCE_DAYS = 7                  # объявление в приложении показываем, когда до конца осталось не больше
HAPP_PROVIDER_ID = "uWtxLsbx"      # из кабинета happ-proxy.com; без него Happ игнорирует настройки приложения ниже
# Настройки приложения Happ (документация Happ, «App management»; работают только с providerid):
# при запуске подключаться к серверу с лучшей задержкой, а задержку мерить через настоящее
# соединение (узел, до которого не проходит рукопожатие, получит n/a и не будет выбран)
HAPP_APP_SETTINGS = {
    "Providerid": HAPP_PROVIDER_ID,
    "Subscription-Autoconnect": "1",
    "Subscription-Autoconnect-Type": "lowestdelay",
    "Subscription-Ping-Onopen-Enabled": "1",
    "Ping-Type": "proxy",
}
UPDATE_INTERVAL_HOURS = 3  # как часто приложение само обновляет подписку (после смены конфигов узлов)


def subscription_headers(ends_at: datetime.datetime, trial_token: str | None = None,
                         now: datetime.datetime | None = None) -> dict:
    """Заголовки, по которым Happ показывает срок подписки, кнопки и сам обновляет подписку.

    ends_at - наивное время в UTC (так хранится в БД). total=0 - без лимита трафика.
    trial_token - у триала с сайта ссылки в бота несут токен (start=web_<токен>), чтобы нажатие
    сразу привязывало триал к аккаунту; у обычной подписки они ведут в меню оплаты.

    Что делает Happ (документация Happ, «App management»): support-url - кнопка справа (значок
    Telegram), profile-web-page-url - кнопка слева, sub-expire + sub-expire-button-link - уведомление
    с кнопкой «Продлить» за 3 дня до конца и после него, announce - текст до 200 символов,
    notification-subs-expire - ежедневное уведомление за 3 дня до конца.
    """
    now = now or datetime.datetime.utcnow()
    expire = int(ends_at.replace(tzinfo=datetime.timezone.utc).timestamp())
    bot_link = f"{BOT_URL}?start=web_{trial_token}" if trial_token else BOT_URL
    action_link = f"{BOT_URL}?start=web_{trial_token}" if trial_token else PAY_URL
    headers = {
        "Subscription-Userinfo": f"upload=0; download=0; total=0; expire={expire}",
        "Profile-Title": PROFILE_TITLE,
        "Profile-Update-Interval": str(UPDATE_INTERVAL_HOURS),
        "Support-Url": bot_link,
        "Profile-Web-Page-Url": action_link,
        "Sub-Expire": "1",
        "Sub-Expire-Button-Link": action_link,
        "Notification-Subs-Expire": "1",
        **HAPP_APP_SETTINGS,
    }
    left = ends_at - now
    text = None
    if trial_token:
        text = f"Бесплатный доступ до {ends_at:%d.%m}. Закрепите его в боте @mirkaprotecbot"
    elif left <= datetime.timedelta(0):
        text = f"Подписка закончилась {ends_at:%d.%m}. Продлите в боте @mirkaprotecbot"
    elif left <= datetime.timedelta(days=ANNOUNCE_DAYS):
        text = f"Подписка до {ends_at:%d.%m}. Продлить: значок слева или бот @mirkaprotecbot"
    if text:
        headers["Announce"] = "base64:" + base64.b64encode(text.encode("utf-8")).decode()
    return headers


def build_vless_links(inbounds: dict, sub_id: str, server_name: str) -> list[str]:
    """Собирает vless-ссылки клиента с данным sub_id из ответа панели (/inbounds/list)."""
    links = []
    for inbound in inbounds["obj"]:

        if inbound["protocol"] != "vless":
            continue

        settings = json.loads(inbound["settings"])
        stream = json.loads(inbound["streamSettings"])

        clients = settings.get("clients", [])

        for client in clients:

            if client["subId"] != sub_id:
                continue

            uuid = client["id"]
            grpc = stream.get("grpcSettings", {})
            reality = stream.get("realitySettings", {})
            service_name = grpc.get("serviceName", "")
            public_key = reality.get("settings", {}).get("publicKey", "")
            fingerprint = reality.get("settings", {}).get("fingerprint", "chrome")

            sni = (
                reality.get("serverNames", [""])[0]
                if reality.get("serverNames")
                else reality.get("settings", {}).get("serverName", "")
            )

            short_ids = reality.get("shortIds", [])
            short_id = short_ids[0]
            host = SERVERS[server_name]["host"]
            port = inbound["port"]
            remark = SERVERS[server_name]["name"]

            vless = (
                f"vless://{uuid}@{host}:{port}"
                f"?type=grpc"
                f"&security=reality"
                f"&pbk={public_key}"
                f"&fp={fingerprint}"
                f"&sni={sni}"
                f"&sid={short_id}"
                f"&serviceName={service_name}"
                f"&encryption=none"
                f"&authority="
                f"&spx=%2F"
                f"#{remark}"
            )

            links.append(vless)
    return links

@subs_router.get("/subs/{token}")
async def get_subscription(token: str):
    async with AsyncSessionLocal() as session:
        result_user = await session.execute(select(User).where(User.token == token))
        user = result_user.scalar_one_or_none()
        now = datetime.datetime.utcnow()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.ends_at:
            user.ends_at = now + datetime.timedelta(days=7)
            user.trial_used = True

        links = []

        for server_name, server in SERVERS.items():
            xui = None
            try:
                result_subs = await session.execute(
                    select(Subscription).where(
                        Subscription.user_id == user.tg_id,
                        Subscription.server_name == server_name))
                sub = result_subs.scalar_one_or_none()

                xui = XUI(server)
                await xui.login()

                if not sub:
                    link = await xui.create_link(
                        client_name=f'TG_{user.tg_id}',
                        tg_id=user.tg_id, ends_at=user.ends_at)

                    sub_id = link.split("/")[-1]
                    vpn = Subscription(user_id=user.tg_id,
                                    server_name=server_name,
                                    sub_id=sub_id,
                                    sub_link=link,
                                    starts_at=now,
                                    is_trial=True,
                                    is_active=True)
                    session.add(vpn)
                    await session.commit()
                    await asyncio.sleep(1)  # Небольшая задержка для обеспечения сохранения данных в БД
                else:
                    sub_id = sub.sub_id

                inbounds = await xui.get_inbounds()
                links.extend(build_vless_links(inbounds, sub_id, server_name))
            except Exception:
                # Одна недоступная панель не должна ронять весь ответ -
                # пользователь всё равно должен получить ссылки с рабочих серверов.
                logger.exception(
                    "Не удалось получить ссылку с сервера %s для пользователя %s",
                    server_name, user.tg_id,
                )
                await notify_admin_throttled(
                    f"node:{server_name}",
                    f"🔴 Узел {SERVERS[server_name]['name']} не ответил при выдаче подписки "
                    f"({type(sys.exc_info()[1]).__name__}). Если повторяется, проверьте панель и доступность сервера.",
                    window=3600)
            finally:
                if xui is not None:
                    await xui.close()

        if not links:
            # Раньше в этом случае пользователь молча получал пустую подписку
            # (ни один сервер не поднялся), а админ никогда об этом не узнавал.
            logger.error("Не удалось выдать ни одной VPN-ссылки пользователю %s", user.tg_id)
            try:
                from main import bot
                await bot.send_message(
                    chat_id=os.getenv('ADMIN_ID'),
                    text=f"⚠️Пользователь {user.tg_id} запросил подписку, но ни одна из {len(SERVERS)} панелей не выдала ссылку — проверьте панели вручную.",
                )
            except Exception:
                logger.exception("Не удалось уведомить админа о пустой подписке для %s", user.tg_id)

        result = "\n".join(links)

        encoded = base64.b64encode(result.encode()).decode()

        return PlainTextResponse(encoded, headers=subscription_headers(user.ends_at))
