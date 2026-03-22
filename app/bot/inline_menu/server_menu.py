from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

on_server_page = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Профиль', callback_data='profile')],
    [InlineKeyboardButton(text="Главное меню", callback_data="back_main_menu")],
    [InlineKeyboardButton(text="Продлить доступ", callback_data="Extend")],
    [InlineKeyboardButton(text="Соглашение", callback_data="Extend")],
])