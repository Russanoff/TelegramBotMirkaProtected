from aiogram import Router, F
from aiogram.filters.callback_data import CallbackQuery
from app.bot.inline_menu.end_subs_menu import step_two


end_subs_callbacks = Router()


@end_subs_callbacks.callback_query(F.data == "Extend")
async def extend_access(callback: CallbackQuery):
    await callback.message.edit_text(text="Выберите срок продления доступа", reply_markup=step_two)
