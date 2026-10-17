from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    # оплата: первая и одна на всю ширину
    [InlineKeyboardButton(text="💸 Пополнить баланс 💸", callback_data="Extend")],
    [InlineKeyboardButton(text="🔗 Ссылка VPN", callback_data="subs"),
     InlineKeyboardButton(text='🖥 Профиль', callback_data='profile')],
    [InlineKeyboardButton(text='🤝 Пригласить друга', callback_data='referral'),
     InlineKeyboardButton(text='⚙️ Поддержка', callback_data='support')],
    [InlineKeyboardButton(text='📢 Новости', url='https://t.me/+OfaQPnkI6s9hNTMy'),
     InlineKeyboardButton(text='❗️ Инструкция', callback_data='vpn_instruction')],
    # [InlineKeyboardButton(text="❗️Для россиян(Белые списки🇺🇸)🚫❗️", callback_data="wlist")],
    #[InlineKeyboardButton(text='Прокси Anty', callback_data='proxy_anty')],
])
