from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

on_server_page = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Профиль', callback_data='profile')],
    [InlineKeyboardButton(text="Главное меню", callback_data="back_main_menu")],
    [InlineKeyboardButton(text="Пополнить баланс", callback_data="Extend")],
])