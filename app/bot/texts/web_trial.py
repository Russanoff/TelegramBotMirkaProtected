web_trial_hint = (
    "✅ Доступ с сайта подключён к вашему аккаунту.\n\n"
    "Ссылка с сайта продолжит работать, заново ничего добавлять не нужно. "
    "Если в приложении Happ что-то не обновилось, обновите подписку. "
    "Дальше доступ продлевается здесь, в боте."
)

# Вернулся пользователь с истёкшей подпиской: пока идёт веб-триал, доступ работает по ссылке с сайта
web_trial_hint_expired = (
    "✅ Доступ с сайта подключён к вашему аккаунту.\n\n"
    "Он работает до {until}. Чтобы не остаться без VPN, нажмите «Пополнить баланс»."
)


def web_trial_hint_text(user, trial_ends_at, now, servers_count: int) -> str:
    """Подсказка после перехода с сайта; пустая строка, если сказать нечего."""
    if user.ends_at is None or user.ends_at > now:
        return web_trial_hint
    if trial_ends_at > now:
        return web_trial_hint_expired.format(until=trial_ends_at.strftime("%d.%m.%Y %H:%M"))
    return ""
