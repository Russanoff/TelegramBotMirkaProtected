from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

step_one = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Продлить доступ", callback_data="Extend")],
    [InlineKeyboardButton(text="Главное меню", callback_data="back_main_menu")]
])

step_two = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="10 дней(50р)", callback_data="10_access")],
    [InlineKeyboardButton(text="30 дней(150р)", callback_data="30_access")],
    [InlineKeyboardButton(text="45 дней(200р)", callback_data="45_access")],
    [InlineKeyboardButton(text="60 дней(260р)", callback_data="60_access")],
    [InlineKeyboardButton(text="90 дней(350р)", callback_data="90_access")],
    [InlineKeyboardButton(text="Главное меню", callback_data="back_main_menu")]
])