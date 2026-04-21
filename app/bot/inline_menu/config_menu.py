from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

config_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Иструкция VPN', callback_data='vpn_instruction')],
    #[InlineKeyboardButton(text='Что такое Anty', callback_data='what_anty')],
    #[InlineKeyboardButton(text='Proxy для TG?', callback_data='tg_instruction')],
    [InlineKeyboardButton(text='В главное меню', callback_data='back_main_menu')],
    [InlineKeyboardButton(text='Поддержка', callback_data='support')]
])