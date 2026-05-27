import asyncio
import aiohttp

BASE = "https://france.mirkaprotected.ru:3354/KO2KCUI6V1HdkLGpGP"

USERNAME = "adminser"
PASSWORD = "Miroslava_101113"

async def main():

    connector = aiohttp.TCPConnector(ssl=False)

    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://france.mirkaprotected.ru:3354",
        "Referer": f"{BASE}/",
        "X-Requested-With": "XMLHttpRequest",
    }

    async with aiohttp.ClientSession(
        connector=connector,
        headers=headers
    ) as session:

        # 1. Открываем панель
        r = await session.get(f"{BASE}/")
        r = await session.get(f"{BASE}/csrf-token")

        csrf_data = await r.json()
        csrf_token = csrf_data["obj"]

        session.headers.update({
            "X-CSRF-Token": csrf_token,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        })

        r = await session.post(
            f"{BASE}/getTwoFactorEnable"
        )

        r = await session.post(
            f"{BASE}/login",
            data={
                "username": USERNAME,
                "password": PASSWORD
            }
        )

        print("LOGIN:", r.status)
        print(await r.text())

        # 6. API TEST
        r = await session.get(
            f"{BASE}/panel/api/inbounds/list"
        )


        print(await r.text())


asyncio.run(main())