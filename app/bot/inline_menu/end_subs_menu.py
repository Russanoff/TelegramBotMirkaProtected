from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

step_one = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="КартаМИР/VISA/СБП🇷🇺🇰🇿🇦🇲🇧🇾🇦🇿", callback_data="card_pay")],
    [InlineKeyboardButton(text="CryptoBot💵(USDT)", callback_data="usdt_pay")],
    [InlineKeyboardButton(text="TelegramStars⭐", callback_data="stars_pay")],
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

# Цифры в скобках должны совпадать со STARS_TARIFFS в app/api_stars/stars_pay.py —
# они специально не импортируются сюда напрямую, чтобы не плодить связи между
# модулем клавиатур и модулем оплаты, но при изменении тарифа поправь оба места.
step_two_stars = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="10 дней(29⭐)", callback_data="10_accessstars")],
    [InlineKeyboardButton(text="30 дней(99⭐)", callback_data="30_accessstars")],
    [InlineKeyboardButton(text="60 дней(199⭐)", callback_data="60_accessstars")],
    [InlineKeyboardButton(text="90 дней(299⭐)", callback_data="90_accessstars")],
    [InlineKeyboardButton(text="365 дней(999⭐)", callback_data="365_accessstars")],
    [InlineKeyboardButton(text="↩️Выйти", callback_data="back_main_menu")]
])
