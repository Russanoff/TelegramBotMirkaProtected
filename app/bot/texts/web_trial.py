web_trial_hint = (
    "✅ Доступ с сайта подключён к вашему аккаунту.\n\n"
    "Вернитесь в приложение Happ и обновите подписку - ссылка та же, "
    "но теперь в ней все локации: {count}. Заново ничего добавлять не нужно."
)

# Вернулся пользователь с истёкшей подпиской: пока идёт веб-триал, работают только его 2 локации
web_trial_hint_expired = (
    "✅ Доступ с сайта подключён к вашему аккаунту.\n\n"
    "Он работает до {until} (2 локации). Чтобы получить все локации ({count}) и не остаться без VPN, "
    "нажмите «Продлить доступ»."
)


def web_trial_hint_text(user, trial_ends_at, now, servers_count: int) -> str:
    """Подсказка после перехода с сайта; пустая строка, если сказать нечего."""
    if user.ends_at is None or user.ends_at > now:
        return web_trial_hint.format(count=servers_count)
    if trial_ends_at > now:
        return web_trial_hint_expired.format(
            until=trial_ends_at.strftime("%d.%m.%Y %H:%M"), count=servers_count)
    return ""
