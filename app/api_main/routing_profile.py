"""Профиль маршрутизации Happ: российские сайты и банки открываются напрямую, остальное идёт через VPN.

Доставка: строка happ://routing/onadd/<base64 JSON> в начале тела подписки (документация Happ, «Routing»).
onadd добавляет профиль и сразу включает его; профиль с тем же именем перезаписывается, поэтому при
изменении списков поднимайте ROUTING_UPDATED (на новое Unix-время). Названия geosite/geoip сверены с базой runetfreedom
(russia-v2ray-rules-dat), а домены, которых в категориях может не быть, перечислены явно.
"""
import base64
import json

ROUTING_NAME = "MirkaProtected: РФ напрямую"
ROUTING_UPDATED = "1793220000"   # Unix-время правки списков; при изменении профиля увеличивать
GEO_BASE = "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download"

# ТОЛЬКО категории, которые есть в любых стандартных geosite-файлах: если Happ запустит ядро с другим файлом, чем
# мы ожидаем, отсутствующая категория (как ru-available-only-inside) не даёт ядру стартовать. Всё остальное - явными доменами.
DIRECT_CATEGORIES = ["category-ru", "private", "apple", "google-play", "steam"]

# явные домены (в geosite.dat они есть, но не в каждой категории; перечислены на случай, если список поменяется)
DIRECT_DOMAINS = [
    # маркетплейсы и магазины
    "ozon.ru", "ozon.com", "ozone.ru", "ozonusercontent.com", "wildberries.ru", "wb.ru", "wbbasket.ru", "wbstatic.net",
    "megamarket.ru", "sbermegamarket.ru", "sbermarket.ru", "avito.ru", "avito.st", "lamoda.ru", "dns-shop.ru",
    "citilink.ru", "mvideo.ru", "eldorado.ru", "detmir.ru", "leroymerlin.ru", "vseinstrumenti.ru", "magnit.ru",
    "5ka.ru", "perekrestok.ru", "vkusvill.ru", "samokat.tech", "lenta.com",
    # банки и платежи
    "sberbank.ru", "sber.ru", "sbrf.ru", "sberbank.com", "tbank.ru", "t-bank.ru", "tinkoff.ru", "tcsbank.ru",
    "vtb.ru", "alfabank.ru", "alfa.bank", "gazprombank.ru", "raiffeisen.ru", "open.ru", "sovcombank.ru", "halvacard.ru",
    "pochtabank.ru", "mkb.ru", "rosbank.ru", "uralsib.ru", "akbars.ru", "psbank.ru", "rshb.ru", "domrfbank.ru",
    "mtsbank.ru", "bspb.ru", "ubrr.ru", "nspk.ru", "mironline.ru", "yoomoney.ru", "yookassa.ru", "qiwi.com",
    "cloudpayments.ru", "tinkoff.com", "sbp.nspk.ru",
    # государство и налоги
    "gosuslugi.ru", "esia.gosuslugi.ru", "mos.ru", "nalog.ru", "nalog.gov.ru", "lknpd.nalog.ru", "pfr.gov.ru", "sfr.gov.ru",
    "gov.ru", "kremlin.ru", "mvd.ru", "fssp.gov.ru",
    # сервисы и медиа
    "yandex.ru", "yandex.com", "ya.ru", "yandex.net", "yastatic.net", "kinopoisk.ru", "ivi.ru", "okko.tv", "wink.ru",
    "rutube.ru", "dzen.ru", "hh.ru", "vk.com", "vk.ru", "ok.ru", "mail.ru", "userapi.com", "vkuser.net", "mycdn.me",
    "2gis.ru", "2gis.com", "rzd.ru", "aeroflot.ru", "tutu.ru", "ozon.travel",
]

PRIVATE_IP = ["geoip:ru", "geoip:private", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16"]


def build_profile() -> dict:
    sites = [f"geosite:{c}" for c in DIRECT_CATEGORIES] + [f"domain:{d}" for d in DIRECT_DOMAINS]
    return {
        "Name": ROUTING_NAME,
        "GlobalProxy": "true",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "RemoteDNSIP": "1.1.1.1",
        "DomesticDNSType": "DoU",
        "DomesticDNSDomain": "",
        "DomesticDNSIP": "77.88.8.8",   # Яндекс.DNS для российских доменов
        "Geoipurl": f"{GEO_BASE}/geoip.dat",
        "Geositeurl": f"{GEO_BASE}/geosite.dat",
        "LastUpdated": ROUTING_UPDATED,
        "DnsHosts": {"cloudflare-dns.com": "1.1.1.1"},
        "DirectSites": sites,
        "DirectIp": PRIVATE_IP,
        "ProxySites": [],
        "ProxyIp": [],
        "BlockSites": [],
        "BlockIp": [],
        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "false",
    }


def routing_line() -> str:
    raw = json.dumps(build_profile(), ensure_ascii=False, separators=(",", ":")).encode()
    return "happ://routing/onadd/" + base64.b64encode(raw).decode()


ROUTING_LINE = routing_line()
