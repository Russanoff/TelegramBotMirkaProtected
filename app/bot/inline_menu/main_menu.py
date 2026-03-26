from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='❗️Инструкция', callback_data='vpn_instruction'),
    InlineKeyboardButton(text="💸Продлить доступ", callback_data="Extend")],
    [InlineKeyboardButton(text="🇵🇱Польша 🔥", callback_data="PL")],
    [InlineKeyboardButton(text="🇳🇱Нидерланды", callback_data="NL")],
    [InlineKeyboardButton(text="🇷🇺Россия", callback_data="RU"),
    InlineKeyboardButton(text="🇺🇸США", callback_data="USA")],
    [InlineKeyboardButton(text="🇫🇮Финляндия", callback_data="FN")],
    [InlineKeyboardButton(text='Telegram', callback_data='proxy_tg')],
    [InlineKeyboardButton(text='🖥Профиль', callback_data='profile'),
    InlineKeyboardButton(text='⚙️Поддержка', callback_data='support')]
    #[InlineKeyboardButton(text='Прокси Anty', callback_data='proxy_anty')],
])

