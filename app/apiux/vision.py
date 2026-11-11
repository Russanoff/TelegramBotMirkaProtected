"""Дополнительные входы на узле: «боевой» Vision (ключ `vision`) и прочие (`extras`, например пересылки PL -> USA/NL).

Клиент в каждом дополнительном входе создаётся с тем же subId, что и в основном входе (email с суффиксом входа),
поэтому ссылку для него находит тот же поиск по subId, а срок продлевается вместе с основным клиентом.
"""
import json

VISION_FLOW = "xtls-rprx-vision"


def extra_inbounds(server: dict) -> list[dict]:
    """Все дополнительные входы узла: {remark, label, suffix, flow}."""
    out = []
    if server.get("vision"):
        out.append({"flow": VISION_FLOW, **server["vision"]})
    for extra in server.get("extras", []):
        out.append({"flow": "", **extra})
    return out


def extra_label(server: dict, inbound_remark: str) -> str | None:
    """Название ссылки для дополнительного входа (None - это основной вход)."""
    return next((e["label"] for e in extra_inbounds(server) if e["remark"] == inbound_remark), None)


def client_emails(server: dict, base_email: str) -> list[str]:
    """Email клиента во всех входах узла: основной + по одному на каждый дополнительный вход."""
    return [base_email] + [base_email + e["suffix"] for e in extra_inbounds(server)]


def vision_labels(servers: dict) -> set[str]:
    return {e["label"] for s in servers.values() for e in extra_inbounds(s)}


def promote_vision_links(links: list[str], servers: dict) -> list[str]:
    """Ссылки дополнительных входов ставим сразу после первой, остальной порядок не меняем."""
    labels = vision_labels(servers)
    extra = [l for l in links if l.rsplit("#", 1)[-1] in labels]
    rest = [l for l in links if l not in extra]
    return rest[:1] + extra + rest[1:]


async def ensure_vision_client(xui, server: dict, inbounds: dict, sub_id: str, base_email: str, tg_id: int, ends_at) -> bool:
    """Создаёт клиента в дополнительных входах, где его ещё нет. True - кто-то создан (список входов надо перечитать)."""
    created = False
    for cfg in extra_inbounds(server):
        inbound = next((i for i in inbounds.get("obj", []) if i.get("remark") == cfg["remark"]), None)
        if inbound is None:
            continue  # вход ещё не создан на панели
        if any(c.get("subId") == sub_id for c in json.loads(inbound.get("settings") or "{}").get("clients", [])):
            continue
        await xui.add_client(inbound_id=inbound["id"], client_name=base_email + cfg["suffix"], flow=cfg["flow"],
                             tg_id=tg_id, ends_at=ends_at, sub_id=sub_id)
        created = True
    return created
