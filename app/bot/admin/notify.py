import logging
import os
import time

logger = logging.getLogger(__name__)

GLOBAL_LIMIT = 30      # не больше стольких уведомлений админу...
GLOBAL_WINDOW = 600    # ...за столько секунд (защита от лавины при массовой поломке)

_throttle: dict[str, list] = {}   # ключ -> [время последней отправки, сколько подавлено после неё]
_recent: list[float] = []         # времена последних отправок


def _admin_id() -> int | None:
    value = os.getenv("ADMIN_ID")
    return int(value) if value and value.isdigit() else None


def _resolve_bot(bot=None):
    if bot is not None:
        return bot
    try:
        # процесс API: бот лежит в main.py. В процессе бота bot передаётся явно (импорт main
        # там создал бы второй экземпляр, потому что main.py запущен как __main__).
        from main import bot as main_bot
        return main_bot
    except Exception:
        logger.exception("Не удалось получить экземпляр бота для уведомления админа")
        return None


async def notify_admin(text: str, bot=None) -> bool:
    """Отправляет сообщение админу. Никогда не бросает исключений."""
    admin = _admin_id()
    target = _resolve_bot(bot)
    if admin is None or target is None:
        return False
    try:
        await target.send_message(chat_id=admin, text=text[:4000])
        return True
    except Exception:
        logger.exception("Не удалось отправить уведомление админу")
        return False


async def notify_admin_throttled(key: str, text: str, bot=None, window: int = 600) -> bool:
    """То же, но одинаковые события (по key) не чаще раза в window секунд.

    Подавленные повторы считаются и дописываются в следующее уведомление.
    """
    now = time.time()
    _recent[:] = [t for t in _recent if now - t < GLOBAL_WINDOW]
    entry = _throttle.get(key)
    if entry and now - entry[0] < window:
        entry[1] += 1
        return False
    if len(_recent) >= GLOBAL_LIMIT:
        if entry:
            entry[1] += 1
        return False
    suppressed = entry[1] if entry else 0
    _throttle[key] = [now, 0]
    _recent.append(now)
    extra = f"\n\n(с прошлого уведомления это повторилось ещё {suppressed} раз)" if suppressed else ""
    return await notify_admin(text + extra, bot)
