from datetime import datetime
from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebTrial(Base):
    """Пробный доступ, выданный с лендинга гостю без Telegram-аккаунта."""

    __tablename__ = "web_trials"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    # JSON {"GE": "<sub_id>", ...} - по каким серверам клиент уже создан
    sub_ids: Mapped[str] = mapped_column(Text, default="{}")
    # заполняется, когда гость открыл бота по deep-link
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    # tg_id пригласившего, если гость пришёл по реферальной ссылке на сайт (/?ref=<tg_id>)
    referrer_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
