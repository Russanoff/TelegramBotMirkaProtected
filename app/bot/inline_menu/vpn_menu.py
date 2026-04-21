from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


vpn_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🇳🇱Нидерланды", callback_data="NL")],
    [InlineKeyboardButton(text="🇵🇱Польша", callback_data="PL")],
    [InlineKeyboardButton(text="🇷🇺Россия", callback_data="RU")],
    [InlineKeyboardButton(text="🇺🇸США", callback_data="USA")],
    [InlineKeyboardButton(text="Финляндия", callback_data="FN")],
    [InlineKeyboardButton(text="На главную", callback_data="back_main_menu")]
])