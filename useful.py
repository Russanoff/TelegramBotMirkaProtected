end_date = vpn.ends_at.strftime("%d.%m.%Y %H:%M")







@callbacks_vpn.callback_query(F.data == 'PL')
async def vpn_menus(callback: CallbackQuery):
    tg_id = callback.from_user.id
    await callback.answer('Вы выбрали Польшу, ожидайте...')

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        now = datetime.utcnow()

        subscribers = await session.execute(select(Subscription).where(
            Subscription.user_id == tg_id,
            Subscription.server_name == 'PL',
            Subscription.is_active == True))

        vpn = subscribers.scalar_one_or_none()

        if not user.ends_at:
            user.ends_at = now + timedelta(days=7)
            user.trial_used = True

        if vpn:
            if user.ends_at and user.ends_at > now:
                end_date = user.ends_at.strftime("%d.%m.%Y %H:%M")
                await callback.message.edit_text(f"{text_link}\n\n`{vpn.sub_link}`\n\n"
                                                 f"Активна до: {end_date}\n\nСтатус: ✅🚀 Активна",
                                                 reply_markup=vpn_menu,
                                                 parse_mode='Markdown')
            else:
                await callback.message.edit_text(text=f"`{vpn.sub_link}`\n\n"
                                                      f"Активна до: {user.ends_at}\n\n"
                                                      f"Статус: 🔴⏳ Подписка истекла!",
                                                 parse_mode='Markdown',
                                                 reply_markup=step_one)

        else:
            server = servers.SERVERS['PL']
            xui = new_client.XUI(server)
            await xui.login()
            link = await xui.create_link(client_name=f'TG_{tg_id}', tg_id=tg_id, ends_at=user.ends_at)

            vpn = Subscription(user_id=user.tg_id,
                               server_name='PL',
                               sub_id=link.split('/')[-1],
                               sub_link=link,
                               starts_at=datetime.utcnow(),
                               is_trial=True,
                               is_active=True)
            session.add(vpn)
            await session.commit()
            await callback.message.edit_text(text=F"{text_link}\n\n`{link}`",
                                             reply_markup=vpn_menu,
                                             parse_mode='Markdown')