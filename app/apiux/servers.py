from dotenv import load_dotenv
import os

load_dotenv()

# Порядок важен: в этом порядке ссылки идут в подписке (первые Германия и Латвия: на
# некоторых домашних сетях в РФ работают только узлы их хостера, остальные - позже).
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
    
    "LT": {
        "name": "🇱🇻Latvija",
        "panel_url": "https://ltv.mirkaprotected.ru:4545/vcQi219B8pAO8MeLE4/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Latvija",
        "sub_base": "https://ltv.mirkaprotected.ru:2096/subScSr/",
        "host": "ltv.mirkaprotected.ru"
    },

    "PL": {
        "name": "🇵🇱Poland",
        "panel_url": "https://89.125.159.161:40184/G7EEoRhzE2XqDTs6Ub/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Poland",
        "sub_base": "https://89.125.159.161:2096/sub/",
        # домен вместо IP: при блокировке адреса достаточно поменять A-запись, клиентские ссылки не меняются
        "host": "poland.mirkaprotected.ru"
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
        "vision": {"remark": "Nederlanden-Vision", "label": "🇳🇱Nederlanden-Боевой", "suffix": "_V"},
    },

    "USA": {
        "name": "🇺🇸USA",
        "panel_url": "https://usa.mirkaprotected.ru:4343/HpmzDrFUCuQxvKiFdy",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "USA",
        "sub_base": "https://usa.mirkaprotected.ru:2096/suBscRibe/",
        "host": "usa.mirkaprotected.ru"
    },

}