import datetime
import json
import asyncio

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

from app.db.models.vpn_clients import Subscription

subs_router = APIRouter()

@subs_router.get("/subs/{token}")
async def get_subscription(token: str):
    async with AsyncSessionLocal() as session:
        result_user = await session.execute(select(User).where(User.token == token))
        user = result_user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        links = []
        
        for server_name, server in SERVERS.items():
            result_subs = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user.tg_id,
                    Subscription.server_name == server_name))
            sub = result_subs.scalar_one_or_none()
            now = datetime.datetime.utcnow()
            
            xui = XUI(server)
            await xui.login()
          
        
            if not sub:
                link = await xui.create_link(
                    client_name=f'TG_{user.tg_id}',
                    tg_id=user.tg_id, ends_at=user.ends_at)

                sub_id = link.split("/")[-1]
                vpn = Subscription(user_id=user.tg_id,
                                server_name=server_name,
                                sub_id=link.split('/')[-1],
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
            for inbound in inbounds["obj"]:

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
                        
        
        result = "\n".join(links)

        encoded = base64.b64encode(result.encode()).decode()

        return PlainTextResponse(encoded)

                


