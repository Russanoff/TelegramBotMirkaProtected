import datetime
import json

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
        
        result_subs = await session.execute(select(Subscription).where(Subscription.user_id == user.tg_id))
        subs = result_subs.scalars().all()
        now = datetime.datetime.utcnow()
        links = []  
        
        if not user.ends_at:
            user.ends_at = now + datetime.timedelta(days=7)
            user.trial_used = True
            

        if subs:
            for sub in subs:

                xui = XUI(SERVERS[sub.server_name])

                await xui.login()

                inbounds = await xui.get_inbounds()

                for inbound in inbounds["obj"]:

                    settings = json.loads(inbound["settings"])
                    stream = json.loads(inbound["streamSettings"])

                    clients = settings.get("clients", [])

                    for client in clients:

                        if client["subId"] != sub.sub_id:
                            continue

                        uuid = client["id"]
                        grpc = stream.get("grpcSettings", {})
                        reality = stream.get("realitySettings", {})
                        service_name = grpc.get("serviceName", "")
                        public_key = reality.get("settings", {}).get("publicKey", "")
                        fingerprint = reality.get("settings", {}).get("fingerprint", "chrome")

                        server_name = (
                            reality.get("serverNames", [""])[0]
                            if reality.get("serverNames")
                            else reality.get("settings", {}).get("serverName", "")
                        )

                        short_ids = reality.get("shortIds", [])
                        short_id = short_ids[0]
                        host = SERVERS[sub.server_name]["host"]
                        port = inbound["port"]
                        remark = SERVERS[sub.server_name]["name"]

                        vless = (
                            f"vless://{uuid}@{host}:{port}"
                            f"?type=grpc"
                            f"&security=reality"
                            f"&pbk={public_key}"
                            f"&fp={fingerprint}"
                            f"&sni={server_name}"
                            f"&sid={short_id}"
                            f"&serviceName={service_name}"
                            f"&encryption=none"
                            f"&authority="
                            f"&spx=%2F"
                            f"#{remark}"
                        )

                        links.append(vless)
                        
                        

    
        else:
             for server_name, server in SERVERS.items():
                 xui = new_client.XUI(server)
                 await xui.login()
                 link = await xui.create_link(client_name=f'TG_{user.tg_id}', tg_id=user.tg_id, ends_at=user.ends_at)

                 vpn = Subscription(user_id=user.tg_id,
                                 server_name=server_name,
                                 sub_id=link.split('/')[-1],
                                 sub_link=link,
                                 starts_at=datetime.utcnow(),
                                 is_trial=True,
                                 is_active=True)
                 session.add(vpn)

                 await session.commit()
                
        
        result = "\n".join(links)

        encoded = base64.b64encode(result.encode()).decode()

        return PlainTextResponse(encoded)

                


