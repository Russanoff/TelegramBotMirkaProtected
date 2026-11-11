from dotenv import load_dotenv
import os

load_dotenv()

# Узел с "hidden": True в подписку не попадает (клиенты на нём не создаются), но остаётся в админке, /fixnode
# и ежедневной проверке, а его панель служит выходом для пересылок. Порядок ссылок в подписке задаёт SUB_ORDER.
SERVERS = {
    "GE": {
        "name": "🇩🇪Germany",
        "panel_url": "https://germany.mirkaprotected.ru:4525/8yVOxHuJrdItrjVKHG/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Germany",
        "sub_base": "https://germany.mirkaprotected.ru:4525:2096/subBbSc/",
        "host": "germany.mirkaprotected.ru"
    },
    
    "RU-USA": {
        "name": "🇺🇸Ru-Usa",
        "panel_url": "https://rukas.mirkaprotected.ru:21394/71GHmuywVL0m06LFCf/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "RuExit",
        "sub_base": "https://rukas.mirkaprotected.ru:2096/subTurNNWWiop/",
        "host": "rukas.mirkaprotected.ru"
    },

    "PL": {
        "name": "🇵🇱Poland",
        "panel_url": "https://89.125.159.161:40184/G7EEoRhzE2XqDTs6Ub/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Poland",
        "sub_base": "https://89.125.159.161:2096/sub/",
        # домен вместо IP: при блокировке адреса достаточно поменять A-запись, клиентские ссылки не меняются
        "host": "poland.mirkaprotected.ru",
        # Пересылки: вход на PL, выход в USA/NL. Адреса USA и NL заблокированы в РФ целиком (проверено 12.11.2026
        # из Енакиево и с российского сервера rukas), а PL доступен. Выходы и маршруты - в шаблоне Xray панели PL.
        "extras": [
            {"remark": "PL-USA", "label": "🇺🇸USA(PL)", "suffix": "_U"},
            {"remark": "PL-NL", "label": "🇳🇱Nederlanden(PL)", "suffix": "_N"},
        ],
    },

    "NL": {
        "name": "🇳🇱Nederlanden",
        "panel_url": "https://panel.mirkaprotected.ru:8443/Tg8fvceLgQdcFALcQ1/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Nederlanden",
        "sub_base": "https://panel.mirkaprotected.ru:2096/sub/",
        "host": "panel.mirkaprotected.ru",
        "hidden": True,  # IP заблокирован в РФ целиком (12.11.2026): в подписке только через PL ("Nederlanden(PL)")
        # Второй вход на том же узле: VLESS TCP + Reality + Vision, SNI - свой домен, dest - панель с настоящим
        # сертификатом. Проходит там, где gRPC + Reality режется (проверено владельцем). Клиент в нём создаётся
        # с тем же subId, что и в основном входе (email с суффиксом), ссылка идёт в подписку отдельной строкой.
        "vision": {"remark": "Nederlanden-Vision", "label": "🇳🇱Nederlanden2", "suffix": "_V"},
    },

    "USA": {
        "name": "🇺🇸USA",
        "panel_url": "https://usa.mirkaprotected.ru:4343/HpmzDrFUCuQxvKiFdy",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "USA",
        "sub_base": "https://usa.mirkaprotected.ru:2096/suBscRibe/",
        "host": "usa.mirkaprotected.ru",
        "hidden": True,  # IP заблокирован в РФ целиком (12.11.2026): в подписке только через PL ("USA(PL)")
        # второй («боевой») вход, как на NL: VLESS TCP + Reality + Vision, SNI - свой домен, dest - панель
        "vision": {"remark": "USA-Vision", "label": "🇺🇸USA2", "suffix": "_V"},
    },

}


# Порядок ссылок в подписке (по названию), сверху самые быстрые и надёжные. Замеры из сети с блокировками РФ
# (Енакиево, 12.11.2026, tools/daily_probe.py): Германия ~450 мс, 13-37 Мбит/с, хостер, который пропускают и
# домашние сети РФ; Польша ~600 мс, 20-36; NL через PL ~700-800 мс, 23-36; USA через PL ~800-1500 мс, 17-32;
# Ru-Usa (rukas -> PL -> USA, двойной каскад) ~650 мс, 9-18. Названия не из списка идут в конце.
SUB_ORDER = ["🇩🇪Germany", "🇵🇱Poland", "🇳🇱Nederlanden(PL)", "🇺🇸USA(PL)", "🇺🇸Ru-Usa"]


def subscription_servers() -> dict:
    """Узлы, которые выдаются в подписке (без скрытых)."""
    return {k: v for k, v in SERVERS.items() if not v.get("hidden")}
