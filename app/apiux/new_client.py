import asyncio
import httpx
import uuid
import time
import json
import secrets
import datetime


class XUI:
    def __init__(self, server: dict):
        self.panel_url = server["panel_url"].rstrip("/")
        self.username = server["username"]
        self.password = server["password"]
        self.remark = server["remark"]
        self.sub_base = server["sub_base"]

        self.client = httpx.AsyncClient(
            base_url=self.panel_url,
            verify=False,
            timeout=155
        )

    async def login(self):
        r = await self.client.post(
            "/login",
            data={
                "username": self.username,
                "password": self.password
            }
        )
        return r.status_code == 200

    async def get_inbounds(self):
        r = await self.client.get("/panel/api/inbounds/list")
        r.raise_for_status()
        return r.json()

    async def add_client(
        self,
        inbound_id: int,
        client_name: str,
        flow: str,
        tg_id: int,
        ends_at: datetime
    ):

        expiry_time = int(ends_at.timestamp() * 1000)
        sub_id = secrets.token_urlsafe(9)
        flow = "xtls-rprx-vision"
        client_uuid = str(uuid.uuid4())

        payload = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": client_uuid,
                    "email": client_name,
                    "flow": flow,
                    "tgId": tg_id,
                    "enable": True,
                    "expiryTime": expiry_time,
                    "subId": sub_id,
                    "limitIp": 0,
                    "totalGB": 0,
                    "comment": "Пробный период"
                }]
            })
        }
        r = await self.client.post(
            "/panel/api/inbounds/addClient",
            json=payload
        )
        r.raise_for_status()
        return {
            "ok": True,
            "client": client_name,
            "sub_id": sub_id,
            "subscription_link": f"{sub_id}",
            "client_id": client_uuid
        }

    async def create_link(self, client_name: str, tg_id: int, ends_at: datetime) -> str:

        r = await self.client.get("/panel/api/inbounds/list")
        r.raise_for_status()
        inbounds = r.json()["obj"]

        inbound_id = None
        for inbound in inbounds:
            if inbound["remark"] == self.remark:
                inbound_id = inbound["id"]
                break

        if inbound_id is None:
            raise Exception("Inbound с таким remark не найден")

        result = await self.add_client(
            inbound_id=inbound_id,
            client_name=client_name,
            flow="xtls-rprx-vision",
            tg_id=tg_id,
            ends_at=ends_at
        )

        return f"{self.sub_base}{result['sub_id']}"

    async def update_expiry(self, client_name: str, ends_at: datetime, subs_id: str):
        expiry_time = int(ends_at.timestamp() * 1000)
        r = await self.client.get("/panel/api/inbounds/list")
        r.raise_for_status()
        inbounds = r.json()["obj"]
        for inbound in inbounds:
            settings = json.loads(inbound["settings"])

            for client in settings["clients"]:
                if client["email"] == client_name:
                    client["enable"] = True
                    client_id = client['id']

                    payload = {
                        "id": inbound["id"],
                        "settings": json.dumps({
                            "clients": [
                                {
                                    "id": client_id,
                                    "expiryTime": expiry_time,
                                    "enable": True,
                                    "flow": 'xtls-rprx-vision',
                                    "email": client_name,
                                    "subId": subs_id,
                                    "comment": 'Повторный доступ'
                                }
                            ]
                        })
                    }

                    r2 = await self.client.post(
                        f"/panel/api/inbounds/updateClient/{client_id}",
                        json=payload
                    )
                    r2.raise_for_status()

                    return True

    async def close(self):
        await self.client.aclose()


