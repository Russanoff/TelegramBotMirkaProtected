
from aiogram import Router, F
from aiogram.filters.callback_data import CallbackQuery
from app.apiux import new_client, servers
from app.bot.texts.config_vpn import text_link
from datetime import timedelta, datetime

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.vpn_clients import Subscription
from app.bot.inline_menu.main_menu import main_menu


callbacks_vpn = Router()


#@callbacks_vpn.callback_query(F.data == 'vpn_menu')
#async def vpn_menus(callback: CallbackQuery):
#    await callback.answer('Выберите локацию')
#    await callback.message.edit_text(text="Выберите локацию", reply_markup=vpn_menu)


@callbacks_vpn.callback_query(F.data.in_(servers.SERVERS.keys()))
async def get_link(callback: CallbackQuery):
    tg_id = callback.from_user.id
    server_name = callback.data
    country_name = servers.SERVERS[server_name]['name']
    await callback.answer(f'Вы выбрали {country_name}, ожидайте...')

    async with AsyncSessionLocal() as session:
        result_user = await session.execute(
            select(User).where(
                User.tg_id == tg_id))
        user = result_user.scalar_one_or_none()
        now = datetime.utcnow()

        result_vpn = await session.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user.tg_id,
                Subscription.server_name == server_name,
                Subscription.is_active == True,
            )
        )
        vpn = result_vpn.scalar_one_or_none()

        if not user.ends_at:
            user.ends_at = now + timedelta(days=7)
            user.trial_used = True

        if vpn:
            if user.ends_at and user.ends_at > now:
                end_date = user.ends_at.strftime("%d.%m.%Y %H:%M")
                await callback.message.edit_text(f"{text_link}\n\n`{vpn.sub_link}`\n\n"
                                                 f"Активна до: {end_date}\n\nСтатус: ✅🚀 Активна",
                                                 reply_markup=main_menu,
                                                 parse_mode='Markdown')
            else:
                await callback.message.edit_text(text=f"`{vpn.sub_link}`\n\n"
                                                      f"Активна до: {user.ends_at}\n\n"
                                                      f"Статус: 🔴⏳ Подписка истекла!",
                                                 parse_mode='Markdown',
                                                 reply_markup=main_menu)

        else:
            server = servers.SERVERS[server_name]
            xui = new_client.XUI(server)
            await xui.login()
            link = await xui.create_link(client_name=f'TG_{tg_id}', tg_id=tg_id, ends_at=user.ends_at)

            vpn = Subscription(user_id=user.tg_id,
                               server_name=server_name,
                               sub_id=link.split('/')[-1],
                               sub_link=link,
                               starts_at=datetime.utcnow(),
                               is_trial=True,
                               is_active=True)
            session.add(vpn)

            await session.commit()
            await callback.message.edit_text(text=F"{text_link}\n\n`{link}`",
                                             reply_markup=main_menu,
                                             parse_mode='Markdown')





