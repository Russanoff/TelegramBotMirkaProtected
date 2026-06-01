from dotenv import load_dotenv
import os

load_dotenv()

SERVERS = {
    "GE": {
        "name": "🇩🇪Germany",
        "panel_url": "https://germany.mirkaprotected.ru:4525/8yVOxHuJrdItrjVKHG/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Germany",
        "sub_base": "https://germany.mirkaprotected.ru:4525/subBbSc/",
        "host": "germany.mirkaprotected.ru"
    },
    
    "PL": {
        "name": "🇵🇱Poland",
        "panel_url": "https://89.125.159.161:40184/G7EEoRhzE2XqDTs6Ub/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Poland",
        "sub_base": "https://89.125.159.161:2096/sub/",
        "host": "89.125.159.161"
    },
    
    "LT": {
        "name": " 🇱🇻Latvija",
        "panel_url": "https://ltv.mirkaprotected.ru:4545/vcQi219B8pAO8MeLE4/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Latvija",
        "sub_base": "https://ltv.mirkaprotected.ru:4545/subScSr/",
        "host": "ltv.mirkaprotected.ru"
    },
    
    "NL": {
        "name": "🇳🇱Nederlanden",
        "panel_url": "https://panel.mirkaprotected.ru:8443/Tg8fvceLgQdcFALcQ1/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "Nederlanden",
        "sub_base": "https://panel.mirkaprotected.ru:2096/sub/",
        "host": "panel.mirkaprotected.ru"
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

    "FR": {
        "name": "🇫🇷France",
        "panel_url": "https://france.mirkaprotected.ru:3454/sXFYWBt0HpR7cpxvlR/",
        "username": os.getenv('ADMIN'),
        "password": os.getenv('PASSWORD'),
        "remark": "France",
        "sub_base": "https://france.mirkaprotected.ru:2096/subSccCribBE/",
        "host": "france.mirkaprotected.ru"
    },

}