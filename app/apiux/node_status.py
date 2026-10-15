"""Состояние узла для админ-меню: панель, xray, клиенты, кто онлайн, SNI. Только чтение."""
import asyncio
import json

from app.apiux.new_client import XUI
from app.apiux.servers import SERVERS


async def node_status(key: str, xui_factory=XUI) -> dict:
    srv = SERVERS[key]
    out = {"key": key, "name": srv["name"], "ok": False}
    xui = xui_factory(srv)
    try:
        async def _read():
            await xui.login()
            inbounds = await xui.get_inbounds()
            return inbounds, await xui.server_status(), await xui.online_clients()

        inbounds, status, online = await asyncio.wait_for(_read(), 40)
        ib = next(i for i in inbounds["obj"] if i["remark"] == srv["remark"])
        stream = json.loads(ib.get("streamSettings") or "{}")
        reality = stream.get("realitySettings", {})
        xray = (status or {}).get("xray") or {}
        out.update(
            ok=True,
            enable=ib["enable"],
            clients=len(json.loads(ib["settings"]).get("clients", [])),
            online=len(online) if isinstance(online, list) else None,
            xray_state=xray.get("state"),
            xray_version=xray.get("version"),
            xray_error=xray.get("errorMsg") or "",
            fingerprint=reality.get("settings", {}).get("fingerprint"),
            sni=(reality.get("serverNames") or [None])[0],
            service_name=stream.get("grpcSettings", {}).get("serviceName"),
            uptime_days=int(((status or {}).get("uptime") or 0) / 86400),
        )
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:80]}"
    finally:
        try:
            await xui.close()
        except Exception:
            pass
    return out


async def all_nodes_status() -> list[dict]:
    return list(await asyncio.gather(*(node_status(k) for k in SERVERS)))
