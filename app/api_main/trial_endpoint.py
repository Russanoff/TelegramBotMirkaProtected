import asyncio
import base64
import datetime
import json
import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from sqlalchemy import func, select

from app.api_main.subs_endpoint import build_vless_links
from app.apiux.new_client import XUI
from app.apiux.servers import SERVERS
from app.db.database import AsyncSessionLocal
from app.db.models.web_trial import WebTrial

logger = logging.getLogger(__name__)

trial_router = APIRouter()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
TRIAL_HOURS = 48
MAX_TRIALS_PER_IP = 2          # за окно IP_WINDOW_HOURS (за одним мобильным NAT сидят многие)
IP_WINDOW_HOURS = 24
PANEL_TIMEOUT = 25             # сек на одну панель, чтобы одна упавшая не вешала страницу
COOKIE_NAME = "trial_token"
BOT_USERNAME = "mirkaprotecbot"
PUBLIC_URL = "https://trial.mirkaprotected.ru"

# Защита от двойного создания клиентов при параллельных запросах одного токена
_locks: dict[str, asyncio.Lock] = {}


def _client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def _client_name(trial: WebTrial) -> str:
    return f"WEB_{trial.token[:10]}"


async def _provision_one(server_name: str, trial: WebTrial):
    """Создаёт клиента на одной панели. Возвращает (server_name, sub_id | None)."""
    xui = XUI(SERVERS[server_name])
    try:
        async def _do():
            await xui.login()
            link = await xui.create_link(
                client_name=_client_name(trial), tg_id=0, ends_at=trial.ends_at)
            return link.split("/")[-1]

        return server_name, await asyncio.wait_for(_do(), PANEL_TIMEOUT)
    except Exception:
        logger.exception("Триал %s: не удалось создать клиента на %s", trial.id, server_name)
        return server_name, None
    finally:
        await xui.close()


async def _ensure_clients(session, trial: WebTrial) -> dict:
    """Досоздаёт клиентов на серверах, где их ещё нет. Возвращает {server: sub_id}."""
    lock = _locks.setdefault(trial.token, asyncio.Lock())
    async with lock:
        sub_ids = json.loads(trial.sub_ids or "{}")
        missing = [name for name in SERVERS if name not in sub_ids]
        if missing:
            results = await asyncio.gather(*(_provision_one(n, trial) for n in missing))
            for name, sub_id in results:
                if sub_id:
                    sub_ids[name] = sub_id
            trial.sub_ids = json.dumps(sub_ids)
            await session.commit()
        return sub_ids


def _payload(trial: WebTrial) -> dict:
    return {
        "sub_url": f"{PUBLIC_URL}/t/{trial.token}",
        "ends_at": trial.ends_at.isoformat() + "Z",
        "bot_url": f"https://t.me/{BOT_USERNAME}?start=web_{trial.token}",
    }


@trial_router.get("/", response_class=HTMLResponse)
async def landing():
    return HTMLResponse((WEB_DIR / "trial.html").read_text(encoding="utf-8"))


@trial_router.get("/static/{name}")
async def static_file(name: str):
    path = (WEB_DIR / "static" / name).resolve()
    if path.parent != (WEB_DIR / "static").resolve() or not path.is_file():
        raise HTTPException(status_code=404)
    from fastapi.responses import FileResponse
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@trial_router.post("/api/trial")
async def create_trial(request: Request):
    now = datetime.datetime.utcnow()
    ip = _client_ip(request)
    cookie = request.cookies.get(COOKIE_NAME)

    async with AsyncSessionLocal() as session:
        trial = None
        if cookie:
            trial = (await session.execute(
                select(WebTrial).where(WebTrial.token == cookie))).scalar_one_or_none()

        if trial is None:
            recent = (await session.execute(
                select(func.count(WebTrial.id)).where(
                    WebTrial.ip == ip,
                    WebTrial.created_at > now - datetime.timedelta(hours=IP_WINDOW_HOURS)))).scalar()
            if recent >= MAX_TRIALS_PER_IP:
                return JSONResponse(
                    {"error": "С этого адреса уже выдан пробный доступ. Продлить его можно в боте."},
                    status_code=429)

            trial = WebTrial(
                token=secrets.token_urlsafe(12), ip=ip, ends_at=now + datetime.timedelta(hours=TRIAL_HOURS))
            session.add(trial)
            await session.commit()

        if trial.ends_at <= now:
            return JSONResponse(
                {"error": "Пробный доступ закончился. Продлить его можно в боте."}, status_code=410)

        sub_ids = await _ensure_clients(session, trial)
        if not sub_ids:
            return JSONResponse(
                {"error": "Серверы сейчас недоступны, попробуйте через минуту."}, status_code=503)

        response = JSONResponse(_payload(trial))
        response.set_cookie(
            COOKIE_NAME, trial.token, max_age=30 * 24 * 3600, httponly=True, secure=True, samesite="lax")
        return response


async def _links_for(server_name: str, sub_id: str) -> list[str]:
    xui = XUI(SERVERS[server_name])
    try:
        async def _do():
            await xui.login()
            return build_vless_links(await xui.get_inbounds(), sub_id, server_name)

        return await asyncio.wait_for(_do(), PANEL_TIMEOUT)
    except Exception:
        logger.exception("Триал: не удалось получить ссылку с %s", server_name)
        return []
    finally:
        await xui.close()


@trial_router.get("/t/{token}")
async def trial_subscription(token: str):
    now = datetime.datetime.utcnow()
    async with AsyncSessionLocal() as session:
        trial = (await session.execute(
            select(WebTrial).where(WebTrial.token == token))).scalar_one_or_none()
        if trial is None:
            raise HTTPException(status_code=404, detail="Not found")
        if trial.ends_at <= now:
            raise HTTPException(status_code=410, detail="Trial expired")

        sub_ids = await _ensure_clients(session, trial)

    per_server = await asyncio.gather(*(_links_for(n, s) for n, s in sub_ids.items()))
    links = [link for chunk in per_server for link in chunk]
    return PlainTextResponse(base64.b64encode("\n".join(links).encode()).decode())
