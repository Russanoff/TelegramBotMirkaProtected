import httpx
import asyncio
from app.apiux.servers import SERVERS
import json
import datetime
import time


async def get_google():
    async with httpx.AsyncClient(base_url=SERVERS['NL']['panel_url']) as client:
        r = await client.post(url='/login', data={
            "username": 'adminser',
            "password": 'Miroslava_101113'
        })

        if r.status_code:
            print('Вошли в панель Нидерланды')

        r = await client.get("/panel/api/inbounds/list")
        data = r.json()

        inbound = data["obj"][0]

        settings = json.loads(inbound["settings"])

        found = False

        for c in settings["clients"]:
            if c["id"] == '2ec9ae58-5d9f-4420-8bda-f35c754a36cc':
                c["expiryTime"] = int(time.time() * 1000) + 10 * 86400000
                c["enable"] = True
                found = True
                break

        tg_id = "TG_6627330937"
        flow = "xtls-rprx-vision"

        payload = {
            "id": inbound["id"],
            "settings": json.dumps({
                "clients": [
                    {
                        "id": "2ec9ae58-5d9f-4420-8bda-f35c754a36cc",
                        "email": tg_id,
                        "expiryTime": int(time.time() * 1000) + 30 * 86400000,
                        "enable": True,
                        "flow": flow
                    }
                ]
            })
        }
        print('Что отправляем - ', payload)
        r2 = await client.post(
            f"/panel/api/inbounds/updateClient/{c['id']}",
            json=payload
        )

        print("ОТВЕТ ПАНЕЛИ:", r2.text)


asyncio.run(get_google())

