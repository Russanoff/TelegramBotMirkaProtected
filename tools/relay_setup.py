"""Пересылки: вход на узле ENTRY, выход через основной вход узла EXIT (для обхода блокировок по IP).

  venv/bin/python -W ignore tools/relay_setup.py GE 21443:USA 22443:NL 23443:PL

Для каждой пары PORT:EXIT (идемпотентно):
  - на EXIT в основном входе бессрочный служебный клиент CASCADE_<ENTRY> (не удалять: на нём держится пересылка);
  - на ENTRY вход "<ENTRY>-<EXIT>" на PORT (копия gRPC+Reality основного входа ENTRY) со служебным клиентом
    MONITOR_<ENTRY>-<EXIT> не создаётся: его заведёт tools/daily_probe.py, когда вход появится в servers.py (extras);
  - в шаблоне Xray ENTRY выход "to-<EXIT>" и правило inboundTag -> выход; перезапуск Xray на ENTRY (~1 с обрыва).
Перед изменением шаблона копия кладётся в notes/backups/<дата>/<ENTRY>_template_<время>.json (права 600).
"""
import asyncio, datetime, json, os, sys, uuid, warnings

warnings.filterwarnings("ignore")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO); os.chdir(REPO)
from app.apiux.new_client import XUI
from app.apiux.servers import SERVERS


async def panel(key):
    x = XUI(SERVERS[key])
    if not await asyncio.wait_for(x.login(), 20):
        raise SystemExit(f"{key}: вход в панель не удался")
    return x


async def inbounds(x):
    return (await x.client.get("/panel/api/inbounds/list")).json()["obj"]


async def get_template(x):
    o = (await x.client.post("/panel/xray/")).json()["obj"]
    o = json.loads(o) if isinstance(o, str) else o
    t = o["xraySetting"]
    return json.loads(t) if isinstance(t, str) else t


async def restart(x):
    for path in ("/panel/api/server/restartXrayService", "/server/restartXrayService"):
        try:
            r = await x.client.post(path)
            if r.status_code == 200 and r.text.startswith("{"):
                return r.json().get("success")
        except Exception as e:  # панель может оборвать ответ, если сам запрос шёл через этот узел
            return f"ответ оборван ({type(e).__name__}), проверьте статус"
    return None


def new_client(email, comment):
    return {"id": str(uuid.uuid4()), "email": email, "flow": "", "limitIp": 0, "totalGB": 0, "tgId": 0, "enable": True,
            "subId": uuid.uuid4().hex[:16], "expiryTime": 0, "comment": comment}


async def cascade_outbound(entry, exit_key, tag):
    """Клиент CASCADE_<entry> в основном входе exit_key и outbound к нему."""
    x = await panel(exit_key)
    try:
        ib = next(i for i in await inbounds(x) if i["remark"] == SERVERS[exit_key]["remark"])
        email = f"CASCADE_{entry}"
        cl = next((c for c in json.loads(ib["settings"])["clients"] if c["email"] == email), None)
        if cl is None:
            cl = new_client(email, f"служебный: пересылка {entry}->{exit_key}, не удалять")
            r = (await x.client.post("/panel/api/inbounds/addClient", json={"id": ib["id"], "settings": json.dumps({"clients": [cl]})})).json()
            print(f"{exit_key}: клиент {email} создан:", r.get("success"), r.get("msg"))
        ss = json.loads(ib["streamSettings"]); rs = ss["realitySettings"]
        return {"tag": tag, "protocol": "vless",
                "settings": {"vnext": [{"address": SERVERS[exit_key]["host"], "port": ib["port"],
                                        "users": [{"id": cl["id"], "encryption": "none", "flow": ""}]}]},
                "streamSettings": {"network": ss["network"], "security": "reality",
                                   "realitySettings": {"serverName": rs["serverNames"][0], "fingerprint": rs["settings"].get("fingerprint") or "chrome",
                                                       "publicKey": rs["settings"]["publicKey"], "shortId": rs["shortIds"][0], "spiderX": "/"},
                                   "grpcSettings": {"serviceName": ss.get("grpcSettings", {}).get("serviceName", ""), "multiMode": False}}}
    finally:
        await x.client.aclose()


async def main(entry, pairs):
    outs = {}
    for port, exit_key in pairs:
        outs[exit_key] = await cascade_outbound(entry, exit_key, f"to-{exit_key}")
    x = await panel(entry)
    try:
        ibs = await inbounds(x)
        base = next(i for i in ibs if i["remark"] == SERVERS[entry]["remark"])
        for port, exit_key in pairs:
            remark = f"{entry}-{exit_key}"
            if any(i["remark"] == remark for i in ibs):
                print(f"{entry}: вход {remark} уже есть"); continue
            if any(i["port"] == port for i in ibs):
                raise SystemExit(f"{entry}: порт {port} занят")
            # клиент-заглушка: 3x-ui не создаёт вход без клиентов; бессрочный, служебный
            cl = new_client(f"RELAY_{remark}", "служебный, не удалять")
            payload = {"up": 0, "down": 0, "total": 0, "remark": remark, "enable": True, "expiryTime": 0, "listen": "", "port": port,
                       "protocol": "vless", "settings": json.dumps({"clients": [cl], "decryption": "none", "fallbacks": []}),
                       "streamSettings": base["streamSettings"], "sniffing": base.get("sniffing") or "{}", "allocate": base.get("allocate") or "{}"}
            r = (await x.client.post("/panel/api/inbounds/add", json=payload)).json()
            print(f"{entry}: вход {remark} :{port} создан:", r.get("success"), r.get("msg"))

        t = await get_template(x)
        bdir = os.path.join(REPO, "notes", "backups", f"{datetime.date.today():%Y-%m-%d}"); os.makedirs(bdir, exist_ok=True)
        bp = os.path.join(bdir, f"{entry}_template_{datetime.datetime.now():%H%M%S}.json")
        json.dump(t, open(bp, "w"), indent=1); os.chmod(bp, 0o600)
        changed = False
        for port, exit_key in pairs:
            tag = f"to-{exit_key}"
            cur = next((i for i, o in enumerate(t["outbounds"]) if o.get("tag") == tag), None)
            if cur is None:
                t["outbounds"].append(outs[exit_key]); changed = True
            elif t["outbounds"][cur] != outs[exit_key]:
                t["outbounds"][cur] = outs[exit_key]; changed = True
            rule = {"type": "field", "inboundTag": [f"inbound-{port}"], "outboundTag": tag}
            if rule not in t["routing"]["rules"]:
                t["routing"]["rules"].append(rule); changed = True
        if changed:
            r = (await x.client.post("/panel/xray/update", data={"xraySetting": json.dumps(t)})).json()
            print(f"{entry}: шаблон Xray обновлён:", r.get("success"), r.get("msg"), "| копия до изменения:", os.path.relpath(bp, REPO))
            print(f"{entry}: перезапуск Xray:", await restart(x))
        else:
            os.remove(bp); print(f"{entry}: шаблон уже в порядке")
    finally:
        await x.client.aclose()


if __name__ == "__main__":
    entry = sys.argv[1]
    pairs = [(int(p.split(":")[0]), p.split(":")[1]) for p in sys.argv[2:]]
    asyncio.run(main(entry, pairs))
