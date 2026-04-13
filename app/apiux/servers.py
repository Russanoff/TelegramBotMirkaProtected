from dotenv import load_dotenv
import os

load_dotenv()

SERVERS = {
    "NL": {
        "name": "Нидерланды",
        "panel_url": "https://panel.mirkaprotected.ru:8443/Tg8fvceLgQdcFALcQ1/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Нидерланды",
        "sub_base": "https://panel.mirkaprotected.ru:2096/sub/"
    },

    "PL": {
        "name": "Польша",
        "panel_url": "https://89.125.159.161:40184/G7EEoRhzE2XqDTs6Ub/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Польша",
        "sub_base": "https://89.125.159.161:2096/sub/"
    },

    "RU": {
        "name": "Россия",
        "panel_url": "https://130.49.146.87:61143/6t6PYtzf4c9Pp6bT6K/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Россия",
        "sub_base": "https://130.49.146.87:2096/sub/"
        },

    "USA": {
        "name": "США",
        "panel_url": "https://usa.mirkaprotected.ru:2343/L0Ha2sAAlL1SegIX4e/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "США",
        "sub_base": "https://usa.mirkaprotected.ru:2096/suBscRibe/"
            },

    "OAE": {
        "name": "ОАЭ",
        "panel_url": "https://france.mirkaprotected.ru:3354/KO2KCUI6V1HdkLGpGP/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "ОАЭ",
        "sub_base": "https://france.mirkaprotected.ru:2096/suBscRibers/"
            },

    "wlist": {
        "name": "БелыеСписки",
        "panel_url": "https://antbl.mirkaprotected.ru:24020/IQg9HRJn9556hmjiXX/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "БелыеСписки",
        "sub_base": "https://antbl.mirkaprotected.ru:2096/subbssRibss/"
                }
}

