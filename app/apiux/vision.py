"""Второй («боевой») вход на узле: VLESS TCP + Reality + Vision.

Клиент в нём создаётся с тем же subId, что и в основном входе (email с суффиксом), поэтому ссылку для него
находит тот же поиск по subId, а срок продлевается вместе с основным клиентом.
"""
import json

VISION_FLOW = "xtls-rprx-vision"


def vision_labels(servers: dict) -> set[str]:
    return {s["vision"]["label"] for s in servers.values() if s.get("vision")}


def promote_vision_links(links: list[str], servers: dict) -> list[str]:
    """«Боевые» ссылки ставим сразу после первой, остальной порядок не меняем."""
    labels = vision_labels(servers)
    vision = [l for l in links if l.rsplit("#", 1)[-1] in labels]
    rest = [l for l in links if l not in vision]
    return rest[:1] + vision + rest[1:]


async def ensure_vision_client(xui, server: dict, inbounds: dict, sub_id: str, base_email: str, tg_id: int, ends_at) -> bool:
    """Создаёт клиента во втором входе, если его там ещё нет. True - создан (список входов надо перечитать)."""
    cfg = server.get("vision")
    if not cfg:
        return False
    inbound = next((i for i in inbounds.get("obj", []) if i.get("remark") == cfg["remark"]), None)
    if inbound is None:
        return False  # вход ещё не создан на панели
    for client in json.loads(inbound.get("settings") or "{}").get("clients", []):
        if client.get("subId") == sub_id:
            return False
    await xui.add_client(inbound_id=inbound["id"], client_name=base_email + cfg["suffix"], flow=VISION_FLOW,
                         tg_id=tg_id, ends_at=ends_at, sub_id=sub_id)
    return True
