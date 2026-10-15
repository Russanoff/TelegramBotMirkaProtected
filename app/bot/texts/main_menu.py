from html import escape

SUBS_BASE = "https://subs.mirkaprotected.ru/subs/"


def subscription_link(user) -> str | None:
    token = getattr(user, "token", None)
    # у старых записей в колонке мог остаться False вместо токена
    return f"{SUBS_BASE}{token}" if isinstance(token, str) and token else None


def subscription_block(user) -> str:
    link = subscription_link(user)
    if not link:
        return ""
    return (f"\n\n🔗Ваша ссылка на подписку (нажмите, чтобы скопировать, и добавьте в Happ):\n"
            f"<code>{escape(link)}</code>")


def main_menu_text(user, users_count: int, servers_count: int, now) -> str:
    """Текст главного меню (HTML): статус подписки и ссылка на неё, чтобы не искать в «VPN сервера»."""
    head = f"🟢Активные локации: {servers_count}\n👥Пользователей: {users_count}\n\n"
    if user.ends_at and user.ends_at > now:
        text = head + f"Подписка активна✅🚀\nИстекает - {user.ends_at:%d.%m.%Y %H:%M}"
    elif user.ends_at:
        text = head + "Подписка истекла🔴⏳"
    else:
        text = head + "Нет подписки⏳"
    return text + subscription_block(user)
