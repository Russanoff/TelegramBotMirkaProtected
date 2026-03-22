from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


keyboard_start = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Подтвердить ☑️', callback_data='confirm'),
         InlineKeyboardButton(text='📖 Ознакомиться', callback_data='open_agreements')]
    ]
)

confirm_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Соглашаюсь', callback_data='confirm')]
])

