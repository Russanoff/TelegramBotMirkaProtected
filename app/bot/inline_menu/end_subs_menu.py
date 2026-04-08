from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

step_one = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="КартаМИР/VISA/СБП🇷🇺🇰🇿🇦🇲🇧🇾🇦🇿", callback_data="card_pay")],
    [InlineKeyboardButton(text="USDT", callback_data="usdt_pay")],
    [InlineKeyboardButton(text="↩️Назад", callback_data="back_main_menu")]
])

step_two = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="10 дней(50р)", callback_data="10_access")],
    [InlineKeyboardButton(text="30 дней(150р)", callback_data="30_access")],
    [InlineKeyboardButton(text="45 дней(200р)", callback_data="45_access")],
    [InlineKeyboardButton(text="60 дней(260р)", callback_data="60_access")],
    [InlineKeyboardButton(text="90 дней(350р)", callback_data="90_access")],
    [InlineKeyboardButton(text="↩️Выйти", callback_data="back_main_menu")]
])

step_two_crypto = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="10 дней(1 USDT)", callback_data="1_access_crypto")],
    [InlineKeyboardButton(text="30 дней(4 USDT)", callback_data="4_access_crypto")],
    [InlineKeyboardButton(text="60 дней(5 USDT)", callback_data="5_access_crypto")],
    [InlineKeyboardButton(text="↩️Выйти", callback_data="back_main_menu_crypto")]
])

