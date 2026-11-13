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
        "host": "germany.mirkaprotected.ru",
        # Пересылки через Германию (вход на GE, выход в USA/NL/PL; tools/relay_setup.py). Блокировки по IP в РФ
        # «плавают» (12.11 закрыты NL/USA, 13.11 - PL/USA), а GE доступна оба дня: через неё есть путь в каждую страну.
        "extras": [
            {"remark": "GE-USA", "label": "🇺🇸USA(GE)", "suffix": "_GU"},
            {"remark": "GE-NL", "label": "🇳🇱Nederlanden(GE)", "suffix": "_GN"},
            {"remark": "GE-PL", "label": "🇵🇱Poland(GE)", "suffix": "_GP"},
        ],
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
        # второй («боевой») вход, как на NL: VLESS TCP + Reality + Vision, SNI - свой домен, dest - панель
        "vision": {"remark": "USA-Vision", "label": "🇺🇸USA2", "suffix": "_V"},
    },

}


# Порядок ссылок в подписке (по названию), сверху самые надёжные. Блокировки по IP в РФ меняются день ото дня
# (замеры tools/daily_probe.py из Енакиево: 12.11 закрыты NL/USA, 13.11 - PL/USA), поэтому в подписке все пути,
# а сверху - через Германию, доступную в оба дня. Названия не из списка идут в конце.
SUB_ORDER = [
    "🇩🇪Germany", "🇺🇸USA(GE)", "🇳🇱Nederlanden(GE)", "🇵🇱Poland(GE)",
    "🇳🇱Nederlanden", "🇳🇱Nederlanden2", "🇵🇱Poland", "🇳🇱Nederlanden(PL)", "🇺🇸USA(PL)",
    "🇺🇸Ru-Usa", "🇺🇸USA", "🇺🇸USA2",
]


def subscription_servers() -> dict:
    """Узлы, которые выдаются в подписке (без скрытых)."""
    return {k: v for k, v in SERVERS.items() if not v.get("hidden")}
