"""Ежедневная проверка узлов ИЗ СЕТИ, ГДЕ ЕСТЬ БЛОКИРОВКИ РФ (Мак владельца, Енакиево, Wi-Fi en1 в обход VPN).

Проверяются ровно те ссылки, что получают клиенты: основной вход каждого узла и его дополнительные входы
(Vision, пересылки через PL). Для каждой ссылки: TCP до узла, туннель настоящим клиентом Xray (выходной IP),
скорость. При сбое - причина: блок по IP / DPI (сброс) / настройка сервера (Reality не узнал клиента).

На каждом проверяемом входе держится служебный бессрочный клиент MONITOR_<узел>_<id входа> (создаётся сам).
Итог: сообщение админу в Telegram от бота, строка в notes/monitor/history.jsonl, отчёт notes/monitor/last.txt.

Запуск: cd MirkaProtected && venv/bin/python -W ignore tools/daily_probe.py [--no-send] [GE,PL,...]
Xray: tools/bin/xray (в git не попадает; скачать с github.com/XTLS/Xray-core, сверить SHA-256 с .dgst).
Интерфейс: переменная PROBE_IFACE (по умолчанию en1).
"""
import asyncio, datetime, json, os, re, socket, subprocess, sys, time, urllib.parse, urllib.request, uuid, warnings

warnings.filterwarnings("ignore")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO); os.chdir(REPO)

from dotenv import load_dotenv
from app.apiux.new_client import XUI
from app.apiux.servers import SERVERS
from app.apiux.vision import extra_inbounds
from app.api_main.subs_endpoint import build_vless_links

load_dotenv()
XRAY = os.path.join(REPO, "tools", "bin", "xray")
IFACE = os.environ.get("PROBE_IFACE", "en1")
OUT_DIR = os.path.join(REPO, "notes", "monitor")
PREFIX = "MONITOR_"
IP_BOUND_IF = 25  # macOS
args = [a for a in sys.argv[1:] if not a.startswith("--")]
ONLY = args[0].split(",") if args else list(SERVERS)
SEND = "--no-send" not in sys.argv


def bound_socket():
    s = socket.socket()
    if IFACE:
        s.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(IFACE))
    return s


def vantage():
    """Откуда идёт проверка: IP и провайдер через выбранный интерфейс."""
    try:
        ip = subprocess.run(["curl", "-s", "-m", "10", "--interface", IFACE, "https://api.ipify.org"], capture_output=True, text=True).stdout.strip()
        org = json.loads(urllib.request.urlopen(f"https://ipinfo.io/{ip}/json", timeout=10).read()).get("org", "?")
        return ip, org
    except Exception as e:
        return "", f"нет сети через {IFACE}: {type(e).__name__}"


def tcp(host, port):
    try:
        ip = socket.gethostbyname(host)
        s = bound_socket(); s.settimeout(6); t0 = time.time(); s.connect((ip, port)); s.close()
        return True, int((time.time() - t0) * 1000), ip
    except Exception as e:
        return False, type(e).__name__, None


def outbound_from_link(link):
    u = urllib.parse.urlparse(link); q = dict(urllib.parse.parse_qsl(u.query))
    ss = {"network": q["type"], "security": q.get("security", "reality"),
          "realitySettings": {"serverName": q["sni"], "fingerprint": q.get("fp", "chrome"), "publicKey": q["pbk"], "shortId": q.get("sid", ""), "spiderX": "/"}}
    if IFACE:
        ss["sockopt"] = {"interface": IFACE}
    if q["type"] == "grpc":
        ss["grpcSettings"] = {"serviceName": q.get("serviceName", "")}
    return {"protocol": "vless", "settings": {"vnext": [{"address": u.hostname, "port": u.port,
            "users": [{"id": u.username, "encryption": "none", "flow": q.get("flow", "")}]}]}, "streamSettings": ss}


def tunnel(ob):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); lp = s.getsockname()[1]; s.close()
    cfg = {"log": {"loglevel": "warning"}, "inbounds": [{"listen": "127.0.0.1", "port": lp, "protocol": "socks"}], "outbounds": [ob]}
    cp = os.path.join(OUT_DIR, f".run_{lp}.json"); json.dump(cfg, open(cp, "w")); os.chmod(cp, 0o600)
    lg = cp.replace(".json", ".log")
    p = subprocess.Popen([XRAY, "run", "-c", cp], stdout=open(lg, "w"), stderr=subprocess.STDOUT, cwd=os.path.dirname(XRAY))
    try:
        for _ in range(40):
            try: socket.create_connection(("127.0.0.1", lp), timeout=0.3).close(); break
            except OSError: time.sleep(0.2)
        px = ["--socks5-hostname", f"127.0.0.1:{lp}"]
        for _ in range(2):
            t0 = time.time()
            ip = subprocess.run(["curl", "-s", "-m", "15", *px, "https://api.ipify.org"], capture_output=True, text=True).stdout.strip()
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", ip):
                ms = int((time.time() - t0) * 1000)
                r = subprocess.run(["curl", "-s", "-m", "25", *px, "-o", "/dev/null", "-w", "%{size_download} %{time_total}",
                                    "https://speed.cloudflare.com/__down?bytes=5000000"], capture_output=True, text=True).stdout.split()
                try: mbit = round(int(r[0]) * 8 / float(r[1]) / 1e6, 1)
                except Exception: mbit = None
                return {"ok": True, "exit": ip, "ms": ms, "mbit": mbit}
        log = open(lg).read()
        if "received real certificate" in log or "processed invalid connection" in log:
            why = "настройка сервера: Reality не узнал клиента (ключи/target/время)"
        elif "connection reset by peer" in log:
            why = "сброс соединения (DPI провайдера)"
        elif "i/o timeout" in log or "deadline exceeded" in log.lower():
            why = "тайм-аут внутри туннеля"
        else:
            why = "туннель не открылся"
        return {"ok": False, "why": why}
    finally:
        p.terminate(); p.wait(timeout=5)
        for f in (cp, lg):
            try: os.remove(f)
            except OSError: pass


async def node_targets(key, srv):
    """[(название, ссылка)] для основного и дополнительных входов; служебный клиент создаётся при необходимости."""
    x = XUI(srv)
    try:
        if not await asyncio.wait_for(x.login(), 20):
            raise RuntimeError("панель: вход не удался")
        inb = await x.get_inbounds()
        wanted = [srv["remark"]] + [e["remark"] for e in extra_inbounds(srv)]
        flows = {srv["remark"]: ""} | {e["remark"]: e["flow"] for e in extra_inbounds(srv)}
        out = []
        for remark in wanted:
            ib = next((i for i in inb["obj"] if i["remark"] == remark), None)
            if ib is None:
                out.append((remark, None)); continue
            email = f"{PREFIX}{key}_{ib['id']}"
            cl = next((c for c in json.loads(ib["settings"])["clients"] if c["email"] == email), None)
            if cl is None:
                cl = {"id": str(uuid.uuid4()), "email": email, "flow": flows[remark], "limitIp": 0, "totalGB": 0, "tgId": 0, "enable": True,
                      "subId": uuid.uuid4().hex[:16], "expiryTime": 0, "comment": "ежедневная проверка из РФ, не удалять"}
                r = await x.client.post("/panel/api/inbounds/addClient", json={"id": ib["id"], "settings": json.dumps({"clients": [cl]})})
                r.raise_for_status(); await asyncio.sleep(2)
                inb = await x.get_inbounds()
            links = build_vless_links(inb, cl["subId"], key)
            out.append((remark, links[0] if links else None))
        return out
    finally:
        await x.client.aclose()


def fmt(r):
    if r.get("skip"):
        return f"⚪ {r['label']}: {r['skip']}"
    if r["ok"]:
        sp = f", {r['mbit']} Мбит/с" if r.get("mbit") is not None else ""
        return f"✅ {r['label']}: {r['ms']} мс{sp}"
    return f"❌ {r['label']}: {r['why']}"


def send(text):
    tok, chat = os.getenv("BOT_TOKEN"), os.getenv("ADMIN_ID")
    data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=20).read()


async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    started = datetime.datetime.now()
    vip, vorg = vantage()
    node_ips = set()
    results = []
    for key in ONLY:
        srv = SERVERS[key]
        try:
            targets = await node_targets(key, srv)
        except Exception as e:
            results.append({"node": key, "label": srv["name"], "hidden": bool(srv.get("hidden")), "ok": False, "why": f"панель недоступна ({type(e).__name__})"}); continue
        for remark, link in targets:
            label = (urllib.parse.unquote(link.rsplit("#", 1)[1]) if link else remark)
            hidden = bool(srv.get("hidden"))
            if not link:
                results.append({"node": key, "label": label, "hidden": hidden, "skip": "вход не найден на панели"}); continue
            u = urllib.parse.urlparse(link)
            ok, info, ip = await asyncio.to_thread(tcp, u.hostname, u.port)
            if ip: node_ips.add(ip)
            if not ok:
                why = "IP узла недоступен (блокировка по IP)" if info in ("timeout", "TimeoutError") else f"TCP: {info}"
                results.append({"node": key, "label": label, "hidden": hidden, "ok": False, "why": why}); continue
            r = await asyncio.to_thread(tunnel, outbound_from_link(link))
            results.append({"node": key, "label": label, "hidden": hidden, **r})

    bad_vantage = (not vip) or vip in node_ips
    prev = None
    hist = os.path.join(OUT_DIR, "history.jsonl")
    if os.path.exists(hist):
        lines = open(hist).read().strip().splitlines()
        prev = json.loads(lines[-1]) if lines else None
    prev_ok = {r["label"]: r.get("ok") for r in (prev or {}).get("results", [])}

    head = f"🛰 Проверка узлов {started:%d.%m %H:%M} из {vip or '?'} ({vorg})"
    if bad_vantage:
        head += f"\n⚠️ Проверка идёт НЕ из сети с блокировками (интерфейс {IFACE}): результаты не показывают картину в РФ."
    from app.apiux.servers import SUB_ORDER
    rank = {l: i for i, l in enumerate(SUB_ORDER)}
    shown = sorted([r for r in results if not r.get("hidden")], key=lambda r: rank.get(r["label"], len(rank)))
    hidden = [r for r in results if r.get("hidden")]
    body = ["В подписке (по порядку):", *[fmt(r) for r in shown]]
    if hidden:
        body += ["", "Скрыты из подписки (проверяются, вдруг разблокируют):", *[fmt(r) for r in hidden]]
    changes = [f"{'🟢 заработал' if r.get('ok') else '🔴 перестал работать'}: {r['label']}" for r in results
               if not r.get("skip") and r["label"] in prev_ok and prev_ok[r["label"]] != r.get("ok")]
    ok_n = sum(1 for r in shown if r.get("ok")); all_n = sum(1 for r in shown if not r.get("skip"))
    text = "\n".join([head, f"В подписке работает {ok_n} из {all_n}", *(["Изменения со вчера:", *changes] if changes else []), "", *body])

    rec = {"at": started.isoformat(timespec="seconds"), "vantage": vip, "org": vorg, "bad_vantage": bad_vantage, "results": results}
    with open(hist, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    open(os.path.join(OUT_DIR, "last.txt"), "w").write(text + "\n")
    print(text)
    if SEND:
        try: send(text)
        except Exception as e: print("Telegram: не отправлено:", type(e).__name__, e)

asyncio.run(main())
