"""Сквозная проверка узлов настоящим клиентом Xray (запускать на сервере бота).

На панелях создаётся временный клиент PROBE_... (на 1 час) и в конце удаляется. Через каждый узел с каждым
отпечатком uTLS делается запрос к api.ipify.org: выходной IP должен совпасть с IP узла.

Подготовка (один раз, версия как на узлах):
  mkdir -p /tmp/xraytest && cd /tmp/xraytest
  curl -sLO https://github.com/XTLS/Xray-core/releases/download/v25.12.8/Xray-linux-64.zip
  curl -sLO https://github.com/XTLS/Xray-core/releases/download/v25.12.8/Xray-linux-64.zip.dgst
  # сверить SHA-256 архива с суммой из .dgst, затем распаковать xray (python3 -m zipfile -e Xray-linux-64.zip .)
Запуск:
  cd /root/TelegramBotMirkaProtected && PYTHONPATH=. venv/bin/python -W ignore tools/node_e2e_probe.py [GE,PL,...]
После работы удалить /tmp/xraytest.
"""
import asyncio, datetime, json, os, re, secrets, socket, subprocess, sys, time

from app.apiux.new_client import XUI
from app.apiux.servers import SERVERS

XRAY = "/tmp/xraytest/xray"
FPS = ["chrome", "firefox", "safari", "ios", "android", "edge", "random"]
CURL_TIMEOUT = 12
ONLY = sys.argv[1].split(",") if len(sys.argv) > 1 else list(SERVERS)


def free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def make_config(port, host, node_port, uid, sni, fp, pbk, sid, svc):
    return {
        "log": {"loglevel": "debug"},
        "inbounds": [{"listen": "127.0.0.1", "port": port, "protocol": "socks", "settings": {"udp": False}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": host, "port": node_port, "users": [{"id": uid, "encryption": "none"}]}]},
            "streamSettings": {
                "network": "grpc", "security": "reality",
                "realitySettings": {"serverName": sni, "fingerprint": fp, "publicKey": pbk, "shortId": sid, "spiderX": "/"},
                "grpcSettings": {"serviceName": svc},
            }}],
    }


def probe(cfg: dict, port: int) -> dict:
    cfg_path, log_path = f"/tmp/xraytest/c_{port}.json", f"/tmp/xraytest/l_{port}.log"
    json.dump(cfg, open(cfg_path, "w"))
    log = open(log_path, "w")
    proc = subprocess.Popen([XRAY, "run", "-c", cfg_path], stdout=log, stderr=log, cwd="/tmp/xraytest")
    out = {"ok": False}
    try:
        for _ in range(40):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.3).close(); break
            except OSError:
                time.sleep(0.2)
        t0 = time.time()
        r = subprocess.run(["curl", "-s", "-m", str(CURL_TIMEOUT), "--socks5-hostname", f"127.0.0.1:{port}", "-w", "\n%{http_code}",
                            "https://api.ipify.org"], capture_output=True, text=True)
        out["ms"] = int((time.time() - t0) * 1000)
        body, _, code = r.stdout.rpartition("\n")
        out["code"], out["curl_exit"] = code, r.returncode
        if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", body.strip()):
            out["ok"], out["ip"] = True, body.strip()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        log.close()
    noise = re.compile(r"deprecated|Reading config|started|accepted|Xray 25|unified platform|app/dns|transport/internet/tcp: dialing|proxy/socks|app/proxyman|lookup|DNS", re.I)
    lines = [l for l in open(log_path).read().splitlines() if re.search(r"fail|error|reality|handshake|timeout|refused|reset|EOF|closed|invalid|mismatch|verif", l, re.I) and not noise.search(l)]
    out["log"] = re.sub(r"^\d{4}/\d\d/\d\d \d\d:\d\d:\d\d(\.\d+)? ", "", lines[-1])[:170] if lines else ""
    return out


async def test_node(key: str) -> dict:
    srv = SERVERS[key]
    x = XUI(srv)
    res = {"key": key, "rows": [], "cleanup": "n/a"}
    created = None
    try:
        await asyncio.wait_for(x.login(), 20)
        inbounds = (await x.get_inbounds())["obj"]
        ib = next(i for i in inbounds if i["remark"] == srv["remark"])
        ss = json.loads(ib["streamSettings"]); r = ss["realitySettings"]
        pbk, sid, sni = r["settings"]["publicKey"], r["shortIds"][0], r["serverNames"][0]
        svc, panel_fp = ss["grpcSettings"]["serviceName"], r["settings"]["fingerprint"]
        res["info"] = f"SNI={sni} target={r.get('target') or r.get('dest')} svc={svc!r} uTLS(панель)={panel_fp} port={ib['port']}"
        host = srv["host"]; res["node_ip"] = socket.gethostbyname(host)
        email = f"PROBE_{key}_{secrets.token_hex(3)}"
        added = await x.add_client(inbound_id=ib["id"], client_name=email, flow="", tg_id=0,
                                   ends_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1))
        created = (ib["id"], added["client_id"], email)
        await asyncio.sleep(3)
        for fp in [panel_fp] + [f for f in FPS if f != panel_fp]:
            port = free_port()
            row = await asyncio.to_thread(probe, make_config(port, host, ib["port"], added["client_id"], sni, fp, pbk, sid, svc), port)
            row["fp"], row["is_panel_fp"] = fp, fp == panel_fp
            res["rows"].append(row)
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:120]}"
    finally:
        if created:
            ib_id, uid, email = created
            try:
                dr = await x.client.post(f"/panel/api/inbounds/{ib_id}/delClient/{uid}")
                chk = next(i for i in (await x.get_inbounds())["obj"] if i["id"] == ib_id)
                left = [c for c in json.loads(chk["settings"]).get("clients", []) if c.get("email", "").startswith("PROBE_")]
                res["cleanup"] = "удалён" if not left else f"НЕ УДАЛЁН ({len(left)}), погаснет сам через час"
            except Exception as e:
                res["cleanup"] = f"ошибка удаления {type(e).__name__}, погаснет сам через час"
        await x.close()
    return res


async def main():
    me = subprocess.run(["curl", "-s", "-m", "8", "https://api.ipify.org"], capture_output=True, text=True).stdout.strip()
    print(f"IP сервера бота (без туннеля): {me}\n")
    # порты свободны на момент выбора, поэтому узлы идут по очереди (так и логи читаются проще)
    for res in await asyncio.gather(*(test_node(k) for k in ONLY)):
        print(f"===== {res['key']} {SERVERS[res['key']]['name']}  IP узла {res.get('node_ip', '?')}")
        print(f"   {res.get('info', '')}")
        if "error" in res:
            print(f"   ОШИБКА теста: {res['error']}")
        for row in res["rows"]:
            mark = "✅" if row["ok"] else "❌"
            tag = " (как в панели)" if row["is_panel_fp"] else ""
            detail = f"{row['ms']} мс, выходной IP {row['ip']}" if row["ok"] else (row["log"] or f"curl exit {row.get('curl_exit')}, HTTP {row.get('code')}")
            print(f"   {mark} uTLS {row['fp']:<8}{tag:<15} {detail}")
        print(f"   временный клиент: {res['cleanup']}")
        works = [r["fp"] for r in res["rows"] if r["ok"]]
        print(f"   итог: работает с {len(works)} из {len(res['rows'])} отпечатков" + (f": {', '.join(works)}" if works else ""))


asyncio.run(main())
