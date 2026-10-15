from aiogram.exceptions import TelegramBadRequest


async def safe_edit_text(message, *args, **kwargs):
    """edit_text, который не падает, если текст не изменился (повторное нажатие той же кнопки).

    Без этого Telegram отвечает «message is not modified», обработчик падает с исключением,
    а пользователю кажется, что кнопка не работает.
    """
    try:
        return await message.edit_text(*args, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return None
        raise
