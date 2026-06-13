from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

step_one = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="КартаМИР/VISA/СБП🇷🇺🇰🇿🇦🇲🇧🇾🇦🇿", callback_data="card_pay")],
    [InlineKeyboardButton(text="CryptoBot💵(USDT)", callback_data="usdt_pay")],
    [InlineKeyboardButton(text="↩️Назад", callback_data="back_main_menu")]
])

step_two = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="10 дней(60р)", callback_data="10_access")],
    [InlineKeyboardButton(text="30 дней(199р)", callback_data="30_access")],
    [InlineKeyboardButton(text="60 дней(360р)", callback_data="60_access")],
    [InlineKeyboardButton(text="90 дней(450р)", callback_data="90_access")],
    [InlineKeyboardButton(text="365 дней(1200р)", callback_data="365_access")],
    [InlineKeyboardButton(text="↩️Выйти", callback_data="back_main_menu")]
])

step_two_crypto = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="10 дней(1 USDT)", callback_data="10_accesscry")],
    [InlineKeyboardButton(text="30 дней(4 USDT)", callback_data="30_accesscry")],
    [InlineKeyboardButton(text="60 дней(7 USDT)", callback_data="60_accesscry")],
    [InlineKeyboardButton(text="90 дней(9 USDT)", callback_data="90_accesscry")],
    [InlineKeyboardButton(text="365 дней(12 USDT)", callback_data="365_accesscry")],
    [InlineKeyboardButton(text="↩️Выйти", callback_data="back_main_menu")]
])

