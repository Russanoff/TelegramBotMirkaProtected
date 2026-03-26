import asyncio
import logging
from aiogram import Dispatcher, Bot
from app.bot.handlers.start import router as start_router
from app.bot.call_backs.start_callback import start_menu_callback as smc
from app.bot.call_backs.main_menu_callbacks import main_menu_router as mmr
from app.bot.call_backs.config_callbacks import config_callbacks as ccr
from app.db.database import init_db
from app.bot.call_backs.callbacks_vpn_menu import callbacks_vpn as cvm
from app.bot.call_backs.end_subs_callbacks import end_subs_callbacks as esc
from app.bot.call_backs.pay_callbacks import pay_call
from app.bot.handlers.user_count_handler import router_admin
from dotenv import load_dotenv
import os

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


async def main():
    await init_db()
    dp.include_router(router_admin)
    dp.include_router(pay_call)
    dp.include_router(esc)
    dp.include_router(cvm)
    dp.include_router(start_router)
    dp.include_router(smc)
    dp.include_router(mmr)
    dp.include_router(ccr)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Stop')