from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='❗️Инструкция', callback_data='vpn_instruction'),
    InlineKeyboardButton(text="💸Продлить доступ", callback_data="Extend")],
    [InlineKeyboardButton(text="VPN сервера", callback_data="subs")],
    # [InlineKeyboardButton(text="❗️Для россиян(Белые списки🇺🇸)🚫❗️", callback_data="wlist")],
    # [InlineKeyboardButton(text="Poland 🔥 (Стабильный)", callback_data="PL")],
    # [InlineKeyboardButton(text="🇺🇸USA⚡️(YouTube, Meta)", callback_data="USA")],
    # [InlineKeyboardButton(text="🇫🇷France", callback_data="FR")],
    # [InlineKeyboardButton(text="🇩🇪Germany", callback_data="GE")],
    # [InlineKeyboardButton(text="🇷🇺Россия (Волоколамск)", callback_data="RU")],
    [InlineKeyboardButton(text='Telegram MTProto', callback_data='proxy_tg')],
    [InlineKeyboardButton(text='🖥Профиль', callback_data='profile'),
    InlineKeyboardButton(text='⚙️Поддержка', callback_data='support')],
    [InlineKeyboardButton(text='Новости', url='https://t.me/+OfaQPnkI6s9hNTMy')],
    #[InlineKeyboardButton(text='Прокси Anty', callback_data='proxy_anty')],
])

