"""Перенастройка Reality-inbound на узле: Service Name, uTLS, Short IDs, пара ключей.

То же, что админ делает руками в панели 3x-ui, когда узел начинает отдавать ошибку.
Ссылки клиентов собираются из панели при каждом обновлении подписки (build_vless_links),
поэтому после замены им достаточно обновить подписку в приложении.
"""
import asyncio
import base64
import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path

from app.apiux.new_client import XUI
from app.apiux.servers import SERVERS

logger = logging.getLogger(__name__)

# популярные отпечатки из списка uTLS панели; редкие (360, qq) не берём
FINGERPRINTS = ("chrome", "firefox", "safari", "ios", "android", "edge")
BACKUP_DIR = Path(__file__).resolve().parents[2] / "backups" / "reality"

# Service Name вида Get_api_Service: <Глагол>_<существительное>_Service
SERVICE_VERBS = ("Get", "Set", "List", "Sync", "Fetch", "Update", "Check", "Push", "Pull", "Load", "Send", "Read")
SERVICE_NOUNS = ("api", "data", "user", "config", "item", "event", "file", "stats", "order", "token",
                 "session", "profile", "message", "report")

_locks: dict[str, asyncio.Lock] = {}


class RotationError(Exception):
    pass


# ---- X25519 (RFC 7748), чтобы не тащить в прод библиотеку ради одной функции ----

_P = 2 ** 255 - 19
_A24 = 121665


def _decode_scalar(k: bytes) -> int:
    b = bytearray(k)
    b[0] &= 248
    b[31] &= 127
    b[31] |= 64
    return int.from_bytes(b, "little")


def x25519(k: bytes, u: bytes) -> bytes:
    scalar = _decode_scalar(k)
    x1 = int.from_bytes(u, "little") & ((1 << 255) - 1)
    x2, z2, x3, z3 = 1, 0, x1, 1
    swap = 0
    for t in reversed(range(255)):
        kt = (scalar >> t) & 1
        swap ^= kt
        if swap:
            x2, x3 = x3, x2
            z2, z3 = z3, z2
        swap = kt
        a = (x2 + z2) % _P
        aa = a * a % _P
        b = (x2 - z2) % _P
        bb = b * b % _P
        e = (aa - bb) % _P
        c = (x3 + z3) % _P
        d = (x3 - z3) % _P
        da = d * a % _P
        cb = c * b % _P
        x3 = (da + cb) ** 2 % _P
        z3 = x1 * (da - cb) ** 2 % _P
        x2 = aa * bb % _P
        z2 = e * (aa + _A24 * e) % _P
    if swap:
        x2, x3 = x3, x2
        z2, z3 = z3, z2
    return (x2 * pow(z2, _P - 2, _P) % _P).to_bytes(32, "little")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def generate_keypair() -> tuple[str, str]:
    """(private, public) в формате Xray: base64url без паддинга."""
    private = bytearray(secrets.token_bytes(32))
    private[0] &= 248
    private[31] &= 127
    private[31] |= 64
    public = x25519(bytes(private), (9).to_bytes(32, "little"))
    return _b64(bytes(private)), _b64(public)


def random_short_ids() -> list[str]:
    lengths = [2, 4, 6, 8, 10, 12, 14, 16]
    secrets.SystemRandom().shuffle(lengths)
    return [secrets.token_hex(n // 2) for n in lengths]


def random_service_name(exclude: str | None = None) -> str:
    """Имя в виде настоящего gRPC-сервиса: Get_api_Service. Не равно прежнему имени узла."""
    while True:
        name = f"{secrets.choice(SERVICE_VERBS)}_{secrets.choice(SERVICE_NOUNS)}_Service"
        if name != exclude:
            return name


def _snapshot(stream: dict) -> dict:
    """Значения, которые меняет перенастройка (для проверки после записи)."""
    reality = stream.get("realitySettings", {})
    return {
        "serviceName": stream.get("grpcSettings", {}).get("serviceName"),
        "fingerprint": reality.get("settings", {}).get("fingerprint"),
        "publicKey": reality.get("settings", {}).get("publicKey"),
        "privateKey": reality.get("privateKey"),
        "shortIds": reality.get("shortIds"),
    }


def _client_ids(inbound: dict) -> list[str]:
    clients = json.loads(inbound["settings"]).get("clients", [])
    return sorted(f"{c.get('id')}|{c.get('email')}|{c.get('subId')}|{c.get('expiryTime')}" for c in clients)


def _find_inbound(inbounds: dict, remark: str) -> dict:
    for inbound in inbounds["obj"]:
        if inbound["remark"] == remark:
            return inbound
    raise RotationError(f"inbound с remark «{remark}» не найден")


def _write_backup(server_key: str, inbound: dict) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"{server_key}-{datetime.utcnow():%Y%m%d-%H%M%S-%f}.json"
    # в файле приватный ключ: только владельцу, и backups/ не коммитится (.gitignore)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"inbound_id": inbound["id"], "streamSettings": inbound["streamSettings"]}, f)
    return str(path)


async def rotate_reality(server_key: str, apply: bool = False, xui_factory=XUI) -> dict:
    """Без apply только описывает, что будет заменено. Секреты в результат не попадают."""
    if server_key not in SERVERS:
        raise RotationError(f"неизвестный узел {server_key}")
    lock = _locks.setdefault(server_key, asyncio.Lock())
    async with lock:
        server = SERVERS[server_key]
        xui = xui_factory(server)
        try:
            await xui.login()
            inbound = _find_inbound(await xui.get_inbounds(), server["remark"])
            stream = json.loads(inbound["streamSettings"])
            if stream.get("security") != "reality" or stream.get("network") != "grpc":
                raise RotationError("inbound не reality/grpc, автоматическая замена не поддерживается")
            before = _snapshot(stream)
            summary = {
                "server": server_key,
                "name": server["name"],
                "inbound_id": inbound["id"],
                "clients": len(json.loads(inbound["settings"]).get("clients", [])),
                "old_fingerprint": before["fingerprint"],
                "old_service_name_len": len(before["serviceName"] or ""),
                "old_short_ids": len(before["shortIds"] or []),
                "applied": False,
            }
            if not apply:
                return summary

            private, public = generate_keypair()
            new_fp = secrets.choice([f for f in FINGERPRINTS if f != before["fingerprint"]])
            new_stream = json.loads(inbound["streamSettings"])
            new_stream.setdefault("grpcSettings", {})["serviceName"] = random_service_name(before["serviceName"])
            reality = new_stream.setdefault("realitySettings", {})
            reality["privateKey"] = private
            reality["shortIds"] = random_short_ids()
            reality.setdefault("settings", {})["publicKey"] = public
            reality["settings"]["fingerprint"] = new_fp
            expected = _snapshot(new_stream)

            summary["backup"] = _write_backup(server_key, inbound)
            summary["new_fingerprint"] = new_fp
            # имя сервиса не секрет: оно и так есть в каждой клиентской ссылке
            summary["new_service_name"] = expected["serviceName"]

            payload = dict(inbound)
            payload["streamSettings"] = json.dumps(new_stream, indent=2)
            answer = await xui.update_inbound(payload)
            if not answer.get("success"):
                raise RotationError(f"панель отклонила изменение: {str(answer.get('msg'))[:120]}")
            summary["applied"] = True

            after = _find_inbound(await xui.get_inbounds(), server["remark"])
            ok = (
                _snapshot(json.loads(after["streamSettings"])) == expected
                and _client_ids(after) == _client_ids(inbound)
                and after["enable"]
            )
            summary["verified"] = ok
            if not ok:
                logger.error("Reality %s: проверка после записи не прошла, откатываю", server_key)
                rollback = dict(inbound)
                back = await xui.update_inbound(rollback)
                summary["rolled_back"] = bool(back.get("success"))
                summary["applied"] = False
            return summary
        finally:
            await xui.close()
